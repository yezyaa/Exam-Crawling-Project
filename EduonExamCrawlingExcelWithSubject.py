from requests_html import HTMLSession
from bs4 import BeautifulSoup
import re
import os
import requests
import pandas as pd

# 여러 개의 주소 배열 받기 위한 준비
def modify_url(original_url, cp):
    # URL에서 숫자 부분을 추출
    numbers = re.findall(r'\d+', original_url)

    if len(numbers) < 2:
        raise ValueError("URL에 필요한 숫자 부분이 존재하지 않습니다.")
    
    # 새로운 URL 구성, cp 값을 포함
    new_url = f"https://eduon.com/itembank/ajax_itemlist/{numbers[0]}/{numbers[1]}/?cp={cp}/"
    return new_url

# 마지막 페이지까지 문제 전체 가져오기
def fetch_questions(url, clear_list=True):
    session = HTMLSession()
    response = session.get(url)
    response.html.render()

    global all_questions
    if clear_list:
        all_questions = []

    # 과목명과 cp 값을 매핑
    subject_mapping = extract_subject(url)

    # 마지막 페이지 번호 찾기
    page_links = response.html.find('a.page-link')
    page_numbers = [int(re.search(r'\d+', link.text).group()) for link in page_links if re.search(r'\d+', link.text)]
    max_page = max(page_numbers, default = 1)

    for cp, subject_name in subject_mapping.items():
        # 페이지를 순회하기 전에 수정된 URL을 사용하여 초기 페이지 데이터를 가져옵니다.
        modified_url = modify_url(url, cp)
        response = session.get(modified_url)

        # 모든 페이지를 순회하면서 문제 목록 추출
        for page in range(1, max_page + 1):
            # 페이지 번호에 따른 요청 URL 설정, cp 값을 포함
            page_url = f"{modified_url}"

            # 페이지 번호를 payload로 설정
            payload = {'hj_check': '', 'npg': page, 'stext': '', 'cp': cp}

            # 페이지 데이터 가져오기
            page_response = session.get(page_url, params=payload)
            page_soup = BeautifulSoup(page_response.content, 'html.parser')

            # 문제 목록 추출
            questions = page_soup.find_all('div', class_='qb_question')
            for question in questions:
                # 여기에서 extract_question 함수를 호출할 때 subject_name도 함께 전달합니다.
                extract_question(question, subject_name)

# 과목 추출 함수
def extract_subject(url):
    session = HTMLSession()
    response = session.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    subject_mapping = {}
    options = soup.find('select', {'name': 'cp'}).find_all('option')
    for option in options:
        if option['value']:  # 빈 값이 아닌 경우만 처리
            full_subject_name = option.text.strip()
            # ': '를 기준으로 분리하고, 뒤쪽 부분만 사용
            subject_name = full_subject_name.split(': ')[-1] if ': ' in full_subject_name else full_subject_name
            subject_mapping[option['value']] = subject_name
    return subject_mapping

# 번호 추출 함수
def extract_question_number(question):
    # 문제 번호 추출
    question_text_elem = question.find('strong', class_='question')
    question_number_elem = question_text_elem.find('span')
    if question_number_elem:
        question_number = question_number_elem.text
    else:
        question_number = ""
    
    # 문제 번호가 1자리인 경우 처리
    if question_number.isdigit() and len(question_number) == 1:
        question_text_elem.find('span').extract()  # span 태그 제거하여 문제 텍스트 정리
        question_number = question_number_elem.text  # 갱신된 문제 번호
    
    return question_number.strip()  # 앞뒤 공백 제거 후 반환

# 문제 추출 함수
def extract_question_text(question):
    # 문제 텍스트 추출
    question_text_elem = question.find('strong', class_='question')
    question_number = extract_question_number(question)  # 문제 번호 추출 함수 호출
    
    # 문제 텍스트에서 번호를 제외한 순수 텍스트 추출
    question_text = question_text_elem.get_text(strip=True)
    if question_number and question_number in question_text:
        question_text = question_text.replace(question_number, '', 1).strip()  # 문제 번호 제거
    
    return question_text

# 지문 추출 함수
def extract_viewbox(question, question_number, reference):
    viewbox_elem = question.find('div', class_='viewbox')
    viewbox_text = ""
    if viewbox_elem:
        images = viewbox_elem.find_all('img')
        text_content = viewbox_elem.get_text(strip=True)
        if images:  # 이미지가 있는 경우
            for img in images:
                img_src = base_url + img['src']
                download_image(img_src, question_number, reference)
        if text_content.strip():  # 텍스트 내용이 있는 경우에만 텍스트 출력
            viewbox_text = text_content.strip()
        elif not images:  # 이미지와 텍스트 내용이 모두 없는 경우
            print("정보 없음")
    return viewbox_text

# 보기 추출 함수
def extract_choices(question):
    choices_text = ""
    choices_elem = question.find('div', class_='sel-answer')
    
    # u 태그 처리: 필요한 경우 u 태그 내의 텍스트를 유지
    for u_tag in choices_elem.find_all('u'):
        u_tag.replace_with(f"<u>{u_tag.text}</u>")

    if choices_elem:
        # 리스트 형식의 보기 처리
        if choices_elem.find('ul', class_='radio_qb'):
            choices_list = choices_elem.find_all('li')
            for choice in choices_list:
                choice_text = choice.get_text(strip=True)
                # 특수 문자를 숫자 형식으로 변환
                choice_text = choice_text.replace('①', '1.').replace('②', '2.').replace('③', '3.').replace('④', '4.').replace('⑤', '5.')
                choices_text += f"{choice_text}\n"
        
        # 테이블 형식의 보기 처리
        elif choices_elem.find('table', class_='table_answer'):
            table = choices_elem.find('table')
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if cells:  # 테이블 행에 셀이 있는 경우만 처리
                    choice_text = ' '.join(cell.get_text(strip=True) for cell in cells)  # 모든 셀 텍스트를 조합
                    # 특수 문자를 숫자 형식으로 변환
                    choice_text = choice_text.replace('①', '1.').replace('②', '2.').replace('③', '3.').replace('④', '4.').replace('⑤', '5.')
                    choices_text += f"{choice_text}\n"
    
    return choices_text.strip()

# 정답 추출 함수
def extract_correct_answer(question):
    # <li> 태그와 <td> 태그에서 class="viewCorrect"를 가진 모든 요소 찾기
    correct_answer_elements = question.select('.viewCorrect')
    for elem in correct_answer_elements:
        correct_answer_text = elem.get_text(strip=True)
        # 특수 기호를 숫자로 변환
        correct_answer = correct_answer_text.replace('①', '1').replace('②', '2').replace('③', '3').replace('④', '4').replace('⑤', '5').strip()
        # 변환된 정답에서 첫 번째 문자(숫자)를 반환
        if correct_answer[0].isdigit():
            return correct_answer[0]
    # 모든 요소를 검토했으나 정답을 찾지 못한 경우
    return ""

# 해설 추출 함수
def extract_explanation(question):
    explanation_elem = question.find('div', class_='q-text view_explanation')
    explanation = explanation_elem.get_text(strip=True) if explanation_elem else ""
    return explanation

# 문제, 지문, 보기를 합친 추출 함수
def combine_question_elements(text, viewbox, choices):
    elements = [text]  # 문제 텍스트는 항상 포함
    if viewbox.strip():  # 지문 텍스트가 비어 있지 않은 경우에만 추가
        elements.append(viewbox)
    if choices.strip():  # 보기 텍스트가 비어 있지 않은 경우에만 추가
        elements.append(choices)
    
    # 각 요소 사이에 두 줄 띄어쓰기를 추가하여 최종 문자열 생성
    combined_content = "\n\n".join(elements)
    return combined_content

# 컨텐츠 최종 출력
def extract_question(question, subject_name):
    global base_url

    # 번호
    # print("\n번호")
    question_number = extract_question_number(question)
    # if question_number:
    #     print(question_number)
    # else:
    #     print("")

    # 문제
    # print("\n문제")
    question_text = extract_question_text(question)
    # if question_text:
    #     print(question_text)
    # else:
    #     print("")

    # 출처
    ref_elem = question.find('span', class_='ref')
    reference = ref_elem.get_text(strip=True) if ref_elem else ""

    # 지문
    # print("\n지문")
    viewbox_text = extract_viewbox(question, question_number, reference)  # 수정된 부분
    # if viewbox_text:
    #     print(viewbox_text)
    # else:
    #     print("")

    # 보기
    # print("\n보기")
    choices_text = extract_choices(question)
    # if choices_text:
    #     print(choices_text)
    # else:
    #     print("")

    # 보기 이미지 다운로드
    choices_images = question.find_all('div', class_='sel-answer')
    choice_number = 1  # 보기 이미지에 대한 고유 번호 초기화
    for choices_elem in choices_images:
        images = choices_elem.find_all('img')
        for img in images:
            img_src = base_url + img['src']
            # 보기 이미지 다운로드 시 choice_number를 파일 이름에 포함
            download_image(img_src, question_number, reference, is_choices=True, choice_number=choice_number)
            choice_number += 1  # 다음 이미지에 대해 고유 번호 증가

    # 정답
    # print("\n정답")
    correct_answer = extract_correct_answer(question)
    # print(correct_answer)

    # 해설
    # print("\n해설")  # "해설" 타이틀은 무조건 출력
    explanation_text = extract_explanation(question)
    # if explanation_text.strip():  # 해설 텍스트 내용이 있는 경우에만 텍스트 출력
    #     print(explanation_text.strip())

    # 해설 이미지 다운로드
    explanation_images = question.find_all('div', class_='q-text view_explanation')
    for explanation_elem in explanation_images:
        images = explanation_elem.find_all('img')
        for img in images:
            img_src = base_url + img['src']
            download_image(img_src, question_number, reference, is_explanation=True)

    # 문제, 지문, 보기를 한 줄씩 띄어서 합치기
    combined_content = combine_question_elements(question_text, viewbox_text, choices_text)

    '''
    # result안에 바로 엑셀파일 저장하는 방법
    # 데이터를 리스트에 추가
    question_data = [question_number, question_text, viewbox_text, choices_text, correct_answer, explanation_text]
    all_questions.append(question_data)

    # 데이터프레임 생성 및 엑셀 파일로 저장
    df = pd.DataFrame(all_questions, columns=['번호', '문제', '지문', '보기', '정답', '해설'])
    clean_reference = re.sub(r'[()]', '', reference).strip()

    # 'result' 폴더 내부에 저장하기 위한 경로 설정
    result_folder = "result"
    if not os.path.exists(result_folder):  # 'result' 폴더가 없으면 생성
        os.makedirs(result_folder)

    # 파일 이름을 설정할 때 'result' 폴더를 포함
    filename = os.path.join(result_folder, f"{clean_reference}.xlsx")

    # 엑셀 파일 저장
    df.to_excel(filename, index=False)
    print(f"엑셀 파일이 생성되었습니다: {filename}")
    '''   
    # 데이터를 리스트에 추가
    question_data = [subject_name, question_number, combined_content, correct_answer, explanation_text, question_text, viewbox_text, choices_text]
    all_questions.append(question_data)

    # 데이터프레임 생성 및 엑셀 파일로 저장
    df = pd.DataFrame(all_questions, columns=['과목', '문제번호', '문제', '정답', '해설', '문제', '지문', '보기'])
    clean_reference = re.sub(r'[()/]', '', reference).strip()

    # 상위 폴더인 'result' 안에 새로운 폴더 생성
    result_folder = "result"
    new_folder = os.path.join(result_folder, clean_reference)
    if not os.path.exists(new_folder):  # 새로운 폴더가 없으면 생성
        os.makedirs(new_folder)

    # 파일 이름을 설정할 때 새로운 폴더를 포함
    filename = os.path.join(new_folder, f"{clean_reference}.xlsx")

    # 엑셀 파일 저장
    df.to_excel(filename, index=False)
    # print(f"엑셀 파일 다운로드: {filename}")

# 이미지 다운로드 (지문, 보기, 해설)
def download_image(img_url, question_number, reference, is_explanation=False, is_choices=False, choice_number=None):
    try:
        # URL에서 파일 확장자 추출
        file_extension = img_url.split(".")[-1].lower()  # 소문자로 변환하여 대소문자 구분 없애기

        # 지원하는 확장자 목록
        supported_extensions = ["png", "jpg", "jpeg", "gif", "svg", "bmp"]

        # 확장자가 지원하는 목록에 없으면 함수 종료
        if file_extension not in supported_extensions:
            print(f"{reference} 지원하지 않는 파일 확장자: {file_extension}")
            return  # 이 경우, 이미지 다운로드를 수행하지 않음

        clean_reference = re.sub(r'[()/]', '', reference).strip()
        directory_path = os.path.join("result", clean_reference, "images", "해설" if is_explanation else "")
        if is_choices:
            directory_path = os.path.join(directory_path, "보기")
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)

        response = requests.get(img_url)
        response.raise_for_status()  # HTTP 오류가 발생하면 예외를 일으킴
        
        # 파일 이름 구성
        if is_choices and choice_number is not None:
            filename = f"{directory_path}/{clean_reference}_보기_{question_number}_{choice_number}.{file_extension}"
        else:
            filename_prefix = "_해설" if is_explanation else ""
            filename = f"{directory_path}/{clean_reference}{filename_prefix}_{question_number}.{file_extension}"


        with open(filename, "wb") as f:
            f.write(response.content)
        # print(f"이미지 다운로드 완료: {filename}")

    except Exception as e:
        print(f"이미지 다운로드 오류: {e}")

    '''
    # result > images 폴더 안에 이미지 저장하는 방법
    # 이미지 다운로드 및 저장
    def download_image(img_url, question_number, reference, is_explanation=False):
        try:
            clean_reference = re.sub(r'[()]', '', reference).strip()
            directory_path = "result/" + "images/" + clean_reference + ("/해설" if is_explanation else "")
            if not os.path.exists(directory_path):
                os.makedirs(directory_path)

            response = requests.get(img_url)
            response.raise_for_status()  # HTTP 오류가 발생하면 예외를 일으킴
            
            file_extension = img_url.split(".")[-1]
            filename_prefix = "_해설" if is_explanation else ""
            filename = f"{directory_path}/{clean_reference}{filename_prefix}_{question_number}.{file_extension}"
            with open(filename, "wb") as f:
                f.write(response.content)
            # print(f"이미지 다운로드 완료: {filename}")
        except Exception as e:
            print(f"이미지 다운로드 오류: {e}")
    '''
# URL 설정
base_url = 'https://eduon.com/'
urls = [
    'https://eduon.com/itembank/itemlist/65/1313/',
    'https://eduon.com/itembank/itemlist/66/1317/',
    'https://eduon.com/itembank/itemlist/65/1312/',
    'https://eduon.com/itembank/itemlist/66/1316/',
    'https://eduon.com/itembank/itemlist/65/1311/',
    'https://eduon.com/itembank/itemlist/66/1315/',
    'https://eduon.com/itembank/itemlist/65/1309/',
    'https://eduon.com/itembank/itemlist/66/1310/',
    'https://eduon.com/itembank/itemlist/65/1969/',
    'https://eduon.com/itembank/itemlist/66/1985/',
    'https://eduon.com/itembank/itemlist/65/1970/',
    'https://eduon.com/itembank/itemlist/66/1973/',
    'https://eduon.com/itembank/itemlist/65/1971/',
    'https://eduon.com/itembank/itemlist/66/1974/',
    'https://eduon.com/itembank/itemlist/66/2499/',
    'https://eduon.com/itembank/itemlist/65/2484/',
    'https://eduon.com/itembank/itemlist/65/2767/',
    'https://eduon.com/itembank/itemlist/189/2776/',
    'https://eduon.com/itembank/itemlist/190/2777/',
    'https://eduon.com/itembank/itemlist/189/2778/',
    'https://eduon.com/itembank/itemlist/190/2779/',
    'https://eduon.com/itembank/itemlist/189/2784/',
    'https://eduon.com/itembank/itemlist/190/2785/',
    'https://eduon.com/itembank/itemlist/95/1560/',
    'https://eduon.com/itembank/itemlist/95/1561/',
    'https://eduon.com/itembank/itemlist/95/1562/',
    'https://eduon.com/itembank/itemlist/95/1563/',
    'https://eduon.com/itembank/itemlist/95/1564/',
    'https://eduon.com/itembank/itemlist/95/1565/',
    'https://eduon.com/itembank/itemlist/95/1566/',
    'https://eduon.com/itembank/itemlist/95/1567/',
    'https://eduon.com/itembank/itemlist/95/1568/',
    'https://eduon.com/itembank/itemlist/95/1723/',
    'https://eduon.com/itembank/itemlist/95/1772/',
    'https://eduon.com/itembank/itemlist/95/1956/',
    'https://eduon.com/itembank/itemlist/95/2151/',
    'https://eduon.com/itembank/itemlist/95/2211/',
    'https://eduon.com/itembank/itemlist/95/2389/',
    'https://eduon.com/itembank/itemlist/95/2753/',
    'https://eduon.com/itembank/itemlist/95/2807/',
    'https://eduon.com/itembank/itemlist/126/2014/',
    'https://eduon.com/itembank/itemlist/126/2015/',
    'https://eduon.com/itembank/itemlist/126/2016/',
    'https://eduon.com/itembank/itemlist/126/2017/',
    'https://eduon.com/itembank/itemlist/126/2018/',
    'https://eduon.com/itembank/itemlist/126/2019/',
    'https://eduon.com/itembank/itemlist/126/2020/',
    'https://eduon.com/itembank/itemlist/126/2021/',
    'https://eduon.com/itembank/itemlist/126/2022/',
    'https://eduon.com/itembank/itemlist/126/2023/',
    'https://eduon.com/itembank/itemlist/126/2024/',
    'https://eduon.com/itembank/itemlist/126/2025/',
    'https://eduon.com/itembank/itemlist/126/2026/',
    'https://eduon.com/itembank/itemlist/126/2027/',
    'https://eduon.com/itembank/itemlist/126/2028/',
    'https://eduon.com/itembank/itemlist/126/2149/',
    'https://eduon.com/itembank/itemlist/126/2150/',
    'https://eduon.com/itembank/itemlist/126/2212/',
    'https://eduon.com/itembank/itemlist/126/2339/',
    'https://eduon.com/itembank/itemlist/126/2430/',
    'https://eduon.com/itembank/itemlist/126/2617/',
    'https://eduon.com/itembank/itemlist/126/2764/',
    'https://eduon.com/itembank/itemlist/126/2801/',
    'https://eduon.com/itembank/itemlist/126/2814/',
    'https://eduon.com/itembank/itemlist/130/2061/',
    'https://eduon.com/itembank/itemlist/130/2062/',
    'https://eduon.com/itembank/itemlist/130/2063/',
    'https://eduon.com/itembank/itemlist/130/2064/',
    'https://eduon.com/itembank/itemlist/130/2065/',
    'https://eduon.com/itembank/itemlist/130/2066/',
    'https://eduon.com/itembank/itemlist/130/2067/',
    'https://eduon.com/itembank/itemlist/130/2068/',
    'https://eduon.com/itembank/itemlist/130/2201/',
    'https://eduon.com/itembank/itemlist/130/2214/',
    'https://eduon.com/itembank/itemlist/147/2401/',
    'https://eduon.com/itembank/itemlist/147/2402/',
    'https://eduon.com/itembank/itemlist/147/2403/',
    'https://eduon.com/itembank/itemlist/147/2404/',
    'https://eduon.com/itembank/itemlist/147/2405/',
    'https://eduon.com/itembank/itemlist/147/2406/',
    'https://eduon.com/itembank/itemlist/147/2407/',
    'https://eduon.com/itembank/itemlist/147/2408/',
    'https://eduon.com/itembank/itemlist/147/2409/',
    'https://eduon.com/itembank/itemlist/147/2411/',
    'https://eduon.com/itembank/itemlist/147/2410/',
    'https://eduon.com/itembank/itemlist/147/2412/',
    'https://eduon.com/itembank/itemlist/147/2413/',
    'https://eduon.com/itembank/itemlist/147/2414/',
    'https://eduon.com/itembank/itemlist/147/2431/',
    'https://eduon.com/itembank/itemlist/147/2428/',
    'https://eduon.com/itembank/itemlist/147/2429/',
    'https://eduon.com/itembank/itemlist/147/2432/',
    'https://eduon.com/itembank/itemlist/63/1080/',
    'https://eduon.com/itembank/itemlist/63/1081/',
    'https://eduon.com/itembank/itemlist/63/1082/',
    'https://eduon.com/itembank/itemlist/63/1083/',
    'https://eduon.com/itembank/itemlist/63/1084/',
    'https://eduon.com/itembank/itemlist/63/1085/',
    'https://eduon.com/itembank/itemlist/63/1086/',
    'https://eduon.com/itembank/itemlist/63/1087/',
    'https://eduon.com/itembank/itemlist/63/1088/',
    'https://eduon.com/itembank/itemlist/63/1108/',
    'https://eduon.com/itembank/itemlist/63/1353/',
    'https://eduon.com/itembank/itemlist/63/1557/',
    'https://eduon.com/itembank/itemlist/63/1558/',
    'https://eduon.com/itembank/itemlist/63/1559/',
    'https://eduon.com/itembank/itemlist/63/1625/',
    'https://eduon.com/itembank/itemlist/63/1822/',
    'https://eduon.com/itembank/itemlist/63/1953/',
    'https://eduon.com/itembank/itemlist/63/1954/',
    'https://eduon.com/itembank/itemlist/63/2349/',
    'https://eduon.com/itembank/itemlist/63/2350/',
    'https://eduon.com/itembank/itemlist/63/2388/',
    'https://eduon.com/itembank/itemlist/63/2618/',
    'https://eduon.com/itembank/itemlist/63/2803/',
    'https://eduon.com/itembank/itemlist/52/951/',
    'https://eduon.com/itembank/itemlist/52/952/',
    'https://eduon.com/itembank/itemlist/52/953/',
    'https://eduon.com/itembank/itemlist/52/954/',
    'https://eduon.com/itembank/itemlist/52/955/',
    'https://eduon.com/itembank/itemlist/52/956/',
    'https://eduon.com/itembank/itemlist/52/1056/',
    'https://eduon.com/itembank/itemlist/52/1057/',
    'https://eduon.com/itembank/itemlist/52/1058/',
    'https://eduon.com/itembank/itemlist/52/1059/',
    'https://eduon.com/itembank/itemlist/52/1060/',
    'https://eduon.com/itembank/itemlist/52/1095/',
    'https://eduon.com/itembank/itemlist/52/1354/',
    'https://eduon.com/itembank/itemlist/52/1355/',
    'https://eduon.com/itembank/itemlist/52/1556/',
    'https://eduon.com/itembank/itemlist/52/1555/',
    'https://eduon.com/itembank/itemlist/52/1592/',
    'https://eduon.com/itembank/itemlist/52/1721/',
    'https://eduon.com/itembank/itemlist/52/1951/',
    'https://eduon.com/itembank/itemlist/52/1952/',
    'https://eduon.com/itembank/itemlist/52/1958/',
    'https://eduon.com/itembank/itemlist/52/2156/',
    'https://eduon.com/itembank/itemlist/52/2155/',
    'https://eduon.com/itembank/itemlist/72/1391/',
    'https://eduon.com/itembank/itemlist/73/1392/',
    'https://eduon.com/itembank/itemlist/74/1393/',
    'https://eduon.com/itembank/itemlist/72/1394/',
    'https://eduon.com/itembank/itemlist/73/1395/',
    'https://eduon.com/itembank/itemlist/74/1396/',
    'https://eduon.com/itembank/itemlist/72/1397/',
    'https://eduon.com/itembank/itemlist/73/1398/',
    'https://eduon.com/itembank/itemlist/74/1399/',
    'https://eduon.com/itembank/itemlist/72/1400/',
    'https://eduon.com/itembank/itemlist/73/1401/',
    'https://eduon.com/itembank/itemlist/74/1402/',
    'https://eduon.com/itembank/itemlist/72/1403/',
    'https://eduon.com/itembank/itemlist/73/1404/',
    'https://eduon.com/itembank/itemlist/74/1405/',
    'https://eduon.com/itembank/itemlist/72/1975/',
    'https://eduon.com/itembank/itemlist/73/1977/',
    'https://eduon.com/itembank/itemlist/74/1979/',
    'https://eduon.com/itembank/itemlist/72/1976/',
    'https://eduon.com/itembank/itemlist/73/1978/',
    'https://eduon.com/itembank/itemlist/74/1980/',
    'https://eduon.com/itembank/itemlist/72/2299/',
    'https://eduon.com/itembank/itemlist/73/2298/',
    'https://eduon.com/itembank/itemlist/74/2297/',
    'https://eduon.com/itembank/itemlist/72/2346/',
    'https://eduon.com/itembank/itemlist/73/2347/',
    'https://eduon.com/itembank/itemlist/74/2348/',
    'https://eduon.com/itembank/itemlist/109/1829/',
    'https://eduon.com/itembank/itemlist/109/1830/',
    'https://eduon.com/itembank/itemlist/109/1831/',
    'https://eduon.com/itembank/itemlist/109/1832/',
    'https://eduon.com/itembank/itemlist/109/1833/',
    'https://eduon.com/itembank/itemlist/109/1834/',
    'https://eduon.com/itembank/itemlist/109/1837/',
    'https://eduon.com/itembank/itemlist/109/1838/',
    'https://eduon.com/itembank/itemlist/109/1839/',
    'https://eduon.com/itembank/itemlist/109/1962/',
    'https://eduon.com/itembank/itemlist/109/1963/',
    'https://eduon.com/itembank/itemlist/109/1964/',
    'https://eduon.com/itembank/itemlist/109/2204/',
    'https://eduon.com/itembank/itemlist/109/2205/',
    'https://eduon.com/itembank/itemlist/109/2209/',
    'https://eduon.com/itembank/itemlist/109/2351/',
    'https://eduon.com/itembank/itemlist/109/2438/',
    'https://eduon.com/itembank/itemlist/109/2717/',
    'https://eduon.com/itembank/itemlist/59/958/',
    'https://eduon.com/itembank/itemlist/59/959/',
    'https://eduon.com/itembank/itemlist/59/960/',
    'https://eduon.com/itembank/itemlist/59/961/',
    'https://eduon.com/itembank/itemlist/59/962/',
    'https://eduon.com/itembank/itemlist/59/963/',
    'https://eduon.com/itembank/itemlist/133/1070/',
    'https://eduon.com/itembank/itemlist/133/1071/',
    'https://eduon.com/itembank/itemlist/133/1072/',
    'https://eduon.com/itembank/itemlist/133/1073/',
    'https://eduon.com/itembank/itemlist/133/1074/',
    'https://eduon.com/itembank/itemlist/133/1075/',
    'https://eduon.com/itembank/itemlist/133/1358/',
    'https://eduon.com/itembank/itemlist/133/1768/',
    'https://eduon.com/itembank/itemlist/133/1769/',
    'https://eduon.com/itembank/itemlist/133/1770/',
    'https://eduon.com/itembank/itemlist/133/1771/',
    'https://eduon.com/itembank/itemlist/133/1957/',
    'https://eduon.com/itembank/itemlist/133/1968/',
    'https://eduon.com/itembank/itemlist/133/2154/',
    'https://eduon.com/itembank/itemlist/128/2035/',
    'https://eduon.com/itembank/itemlist/128/2036/',
    'https://eduon.com/itembank/itemlist/128/2037/',
    'https://eduon.com/itembank/itemlist/128/2038/',
    'https://eduon.com/itembank/itemlist/128/2039/',
    'https://eduon.com/itembank/itemlist/128/2040/',
    'https://eduon.com/itembank/itemlist/128/2041/',
    'https://eduon.com/itembank/itemlist/128/2042/',
    'https://eduon.com/itembank/itemlist/128/2043/',
    'https://eduon.com/itembank/itemlist/128/2044/',
    'https://eduon.com/itembank/itemlist/128/2206/',
    'https://eduon.com/itembank/itemlist/128/2213/',
    'https://eduon.com/itembank/itemlist/128/2390/',
    'https://eduon.com/itembank/itemlist/128/2710/',
    'https://eduon.com/itembank/itemlist/128/2806/',
    'https://eduon.com/itembank/itemlist/97/1626/',
    'https://eduon.com/itembank/itemlist/97/1627/',
    'https://eduon.com/itembank/itemlist/97/1628/',
    'https://eduon.com/itembank/itemlist/97/1629/',
    'https://eduon.com/itembank/itemlist/97/1630/',
    'https://eduon.com/itembank/itemlist/97/1631/',
    'https://eduon.com/itembank/itemlist/97/1632/',
    'https://eduon.com/itembank/itemlist/97/1633/',
    'https://eduon.com/itembank/itemlist/97/1634/',
    'https://eduon.com/itembank/itemlist/97/1635/',
    'https://eduon.com/itembank/itemlist/97/1636/',
    'https://eduon.com/itembank/itemlist/97/1637/',
    'https://eduon.com/itembank/itemlist/97/1638/',
    'https://eduon.com/itembank/itemlist/97/1639/',
    'https://eduon.com/itembank/itemlist/97/2361/',
    'https://eduon.com/itembank/itemlist/97/2362/',
    'https://eduon.com/itembank/itemlist/97/2363/',
    'https://eduon.com/itembank/itemlist/97/2364/',
    'https://eduon.com/itembank/itemlist/97/2365/',
    'https://eduon.com/itembank/itemlist/97/2366/',
    'https://eduon.com/itembank/itemlist/97/2367/',
    'https://eduon.com/itembank/itemlist/97/2477/',
    'https://eduon.com/itembank/itemlist/97/2636/',
    'https://eduon.com/itembank/itemlist/97/2765/',
    'https://eduon.com/itembank/itemlist/97/2802/',
    'https://eduon.com/itembank/itemlist/97/2811/',
    'https://eduon.com/itembank/itemlist/170/2500/',
    'https://eduon.com/itembank/itemlist/170/2501/',
    'https://eduon.com/itembank/itemlist/170/2502/',
    'https://eduon.com/itembank/itemlist/170/2503/',
    'https://eduon.com/itembank/itemlist/170/2504/',
    'https://eduon.com/itembank/itemlist/170/2505/',
    'https://eduon.com/itembank/itemlist/170/2506/',
    'https://eduon.com/itembank/itemlist/170/2507/',
    'https://eduon.com/itembank/itemlist/170/2508/',
    'https://eduon.com/itembank/itemlist/170/2509/',
    'https://eduon.com/itembank/itemlist/170/2510/',
    'https://eduon.com/itembank/itemlist/170/2511/',
    'https://eduon.com/itembank/itemlist/170/2512/',
    'https://eduon.com/itembank/itemlist/170/2513/',
    'https://eduon.com/itembank/itemlist/170/2514/',
    'https://eduon.com/itembank/itemlist/170/2515/',
    'https://eduon.com/itembank/itemlist/170/2516/',
    'https://eduon.com/itembank/itemlist/170/2517/',
    'https://eduon.com/itembank/itemlist/170/2518/',
    'https://eduon.com/itembank/itemlist/170/2519/',
    'https://eduon.com/itembank/itemlist/69/1367/',
    'https://eduon.com/itembank/itemlist/69/1368/',
    'https://eduon.com/itembank/itemlist/69/1369/',
    'https://eduon.com/itembank/itemlist/69/1370/',
    'https://eduon.com/itembank/itemlist/69/1371/',
    'https://eduon.com/itembank/itemlist/69/1372/',
    'https://eduon.com/itembank/itemlist/69/1373/',
    'https://eduon.com/itembank/itemlist/69/1374/',
    'https://eduon.com/itembank/itemlist/69/1375/',
    'https://eduon.com/itembank/itemlist/69/1376/',
    'https://eduon.com/itembank/itemlist/69/1377/',
    'https://eduon.com/itembank/itemlist/69/1378/',
    'https://eduon.com/itembank/itemlist/69/1379/',
    'https://eduon.com/itembank/itemlist/69/1380/',
    'https://eduon.com/itembank/itemlist/69/1381/',
    'https://eduon.com/itembank/itemlist/188/2744/',
    'https://eduon.com/itembank/itemlist/188/2745/',
    'https://eduon.com/itembank/itemlist/188/2746/',
    'https://eduon.com/itembank/itemlist/188/2747/',
    'https://eduon.com/itembank/itemlist/188/2748/',
    'https://eduon.com/itembank/itemlist/188/2749/',
    'https://eduon.com/itembank/itemlist/188/2750/',
    'https://eduon.com/itembank/itemlist/188/2751/',
    'https://eduon.com/itembank/itemlist/188/2752/',
    'https://eduon.com/itembank/itemlist/188/2754/',
    'https://eduon.com/itembank/itemlist/188/2755/',
    'https://eduon.com/itembank/itemlist/188/2756/',
    'https://eduon.com/itembank/itemlist/188/2757/',
    'https://eduon.com/itembank/itemlist/188/2758/',
    'https://eduon.com/itembank/itemlist/188/2759/',
    'https://eduon.com/itembank/itemlist/188/2760/',
    'https://eduon.com/itembank/itemlist/188/2761/',
    'https://eduon.com/itembank/itemlist/188/2762/',
    'https://eduon.com/itembank/itemlist/127/2029/',
    'https://eduon.com/itembank/itemlist/127/2030/',
    'https://eduon.com/itembank/itemlist/127/2031/',
    'https://eduon.com/itembank/itemlist/127/2032/',
    'https://eduon.com/itembank/itemlist/127/2033/',
    'https://eduon.com/itembank/itemlist/127/2034/',
    'https://eduon.com/itembank/itemlist/127/2352/',
    'https://eduon.com/itembank/itemlist/127/2694/',
    'https://eduon.com/itembank/itemlist/64/1102/',
    'https://eduon.com/itembank/itemlist/64/1103/',
    'https://eduon.com/itembank/itemlist/64/1104/',
    'https://eduon.com/itembank/itemlist/64/1105/',
    'https://eduon.com/itembank/itemlist/64/1106/',
    'https://eduon.com/itembank/itemlist/64/2338/',
    'https://eduon.com/itembank/itemlist/64/1107/',
    'https://eduon.com/itembank/itemlist/64/2330/',
    'https://eduon.com/itembank/itemlist/64/2331/',
    'https://eduon.com/itembank/itemlist/64/2332/',
    'https://eduon.com/itembank/itemlist/64/2333/',
    'https://eduon.com/itembank/itemlist/64/2334/',
    'https://eduon.com/itembank/itemlist/64/2335/',
    'https://eduon.com/itembank/itemlist/64/2336/',
    'https://eduon.com/itembank/itemlist/64/2337/',
    'https://eduon.com/itembank/itemlist/64/2342/',
    'https://eduon.com/itembank/itemlist/64/2537/',
    'https://eduon.com/itembank/itemlist/64/2796/',
    'https://eduon.com/itembank/itemlist/181/2697/',
    'https://eduon.com/itembank/itemlist/181/2698/',
    'https://eduon.com/itembank/itemlist/181/2699/',
    'https://eduon.com/itembank/itemlist/181/2700/',
    'https://eduon.com/itembank/itemlist/181/2701/',
    'https://eduon.com/itembank/itemlist/181/2702/',
    'https://eduon.com/itembank/itemlist/181/2704/',
    'https://eduon.com/itembank/itemlist/181/2703/',
    'https://eduon.com/itembank/itemlist/181/2705/',
    'https://eduon.com/itembank/itemlist/181/2706/',
    'https://eduon.com/itembank/itemlist/181/2707/',
    'https://eduon.com/itembank/itemlist/181/2708/',
    'https://eduon.com/itembank/itemlist/108/1823/',
    'https://eduon.com/itembank/itemlist/108/1824/',
    'https://eduon.com/itembank/itemlist/108/1825/',
    'https://eduon.com/itembank/itemlist/108/1826/',
    'https://eduon.com/itembank/itemlist/108/1827/',
    'https://eduon.com/itembank/itemlist/108/1828/',
    'https://eduon.com/itembank/itemlist/108/1966/',
    'https://eduon.com/itembank/itemlist/108/1967/',
    'https://eduon.com/itembank/itemlist/108/2073/',
    'https://eduon.com/itembank/itemlist/108/2203/',
    'https://eduon.com/itembank/itemlist/108/2451/',
    'https://eduon.com/itembank/itemlist/108/2832/',
    'https://eduon.com/itembank/itemlist/119/1872/',
    'https://eduon.com/itembank/itemlist/119/1873/',
    'https://eduon.com/itembank/itemlist/119/1874/',
    'https://eduon.com/itembank/itemlist/119/1876/',
    'https://eduon.com/itembank/itemlist/119/1877/',
    'https://eduon.com/itembank/itemlist/119/1878/',
    'https://eduon.com/itembank/itemlist/119/1879/',
    'https://eduon.com/itembank/itemlist/119/1880/',
    'https://eduon.com/itembank/itemlist/119/1898/',
    'https://eduon.com/itembank/itemlist/119/1881/',
    'https://eduon.com/itembank/itemlist/119/1899/',
    'https://eduon.com/itembank/itemlist/119/1900/',
    'https://eduon.com/itembank/itemlist/119/2387/',
    'https://eduon.com/itembank/itemlist/120/1919/',
    'https://eduon.com/itembank/itemlist/120/1920/',
    'https://eduon.com/itembank/itemlist/120/1921/',
    'https://eduon.com/itembank/itemlist/120/1922/',
    'https://eduon.com/itembank/itemlist/120/1965/',
    'https://eduon.com/itembank/itemlist/120/2208/',
    'https://eduon.com/itembank/itemlist/120/2809/',
    'https://eduon.com/itembank/itemlist/46/769/',
    'https://eduon.com/itembank/itemlist/46/771/',
    'https://eduon.com/itembank/itemlist/46/785/',
    'https://eduon.com/itembank/itemlist/46/787/',
    'https://eduon.com/itembank/itemlist/46/796/',
    'https://eduon.com/itembank/itemlist/46/948/',
    'https://eduon.com/itembank/itemlist/46/988/',
    'https://eduon.com/itembank/itemlist/46/997/',
    'https://eduon.com/itembank/itemlist/46/1000/',
    'https://eduon.com/itembank/itemlist/46/1006/',
    'https://eduon.com/itembank/itemlist/46/1008/',
    'https://eduon.com/itembank/itemlist/46/1093/',
    'https://eduon.com/itembank/itemlist/46/1552/',
    'https://eduon.com/itembank/itemlist/46/1306/',
    'https://eduon.com/itembank/itemlist/46/1322/',
    'https://eduon.com/itembank/itemlist/46/1553/',
    'https://eduon.com/itembank/itemlist/46/1586/',
    'https://eduon.com/itembank/itemlist/46/1717/',
    'https://eduon.com/itembank/itemlist/46/1835/',
    'https://eduon.com/itembank/itemlist/46/1836/',
    'https://eduon.com/itembank/itemlist/46/1961/',
    'https://eduon.com/itembank/itemlist/132/2099/',
    'https://eduon.com/itembank/itemlist/132/2138/',
    'https://eduon.com/itembank/itemlist/132/2207/',
    'https://eduon.com/itembank/itemlist/132/2312/',
    'https://eduon.com/itembank/itemlist/132/2400/',
    'https://eduon.com/itembank/itemlist/132/2536/',
    'https://eduon.com/itembank/itemlist/132/2775/',
    'https://eduon.com/itembank/itemlist/132/2805/',
    'https://eduon.com/itembank/itemlist/48/770/',
    'https://eduon.com/itembank/itemlist/48/772/',
    'https://eduon.com/itembank/itemlist/48/788/',
    'https://eduon.com/itembank/itemlist/48/789/',
    'https://eduon.com/itembank/itemlist/48/797/',
    'https://eduon.com/itembank/itemlist/48/949/',
    'https://eduon.com/itembank/itemlist/48/989/',
    'https://eduon.com/itembank/itemlist/48/998/',
    'https://eduon.com/itembank/itemlist/48/1001/',
    'https://eduon.com/itembank/itemlist/48/1007/',
    'https://eduon.com/itembank/itemlist/48/1033/',
    'https://eduon.com/itembank/itemlist/48/1094/',
    'https://eduon.com/itembank/itemlist/48/1307/',
    'https://eduon.com/itembank/itemlist/48/1323/',
    'https://eduon.com/itembank/itemlist/48/1554/',
    'https://eduon.com/itembank/itemlist/48/1570/',
    'https://eduon.com/itembank/itemlist/48/1587/',
    'https://eduon.com/itembank/itemlist/48/1718/',
    'https://eduon.com/itembank/itemlist/48/1840/',
    'https://eduon.com/itembank/itemlist/48/1891/',
    'https://eduon.com/itembank/itemlist/48/1892/',
    'https://eduon.com/itembank/itemlist/48/2139/',
    'https://eduon.com/itembank/itemlist/48/2157/',
    'https://eduon.com/itembank/itemlist/180/2651/',
    'https://eduon.com/itembank/itemlist/180/2652/',
    'https://eduon.com/itembank/itemlist/180/2653/',
    'https://eduon.com/itembank/itemlist/180/2654/',
    'https://eduon.com/itembank/itemlist/180/2655/',
    'https://eduon.com/itembank/itemlist/180/2656/',
    'https://eduon.com/itembank/itemlist/180/2657/',
    'https://eduon.com/itembank/itemlist/180/2658/',
    'https://eduon.com/itembank/itemlist/180/2659/',
    'https://eduon.com/itembank/itemlist/180/2660/',
    'https://eduon.com/itembank/itemlist/180/2661/',
    'https://eduon.com/itembank/itemlist/180/2662/',
    'https://eduon.com/itembank/itemlist/180/2663/',
    'https://eduon.com/itembank/itemlist/180/2664/',
    'https://eduon.com/itembank/itemlist/180/2665/',
    'https://eduon.com/itembank/itemlist/180/2666/',
    'https://eduon.com/itembank/itemlist/180/2667/',
    'https://eduon.com/itembank/itemlist/180/2668/',
    'https://eduon.com/itembank/itemlist/180/2669/',
    'https://eduon.com/itembank/itemlist/180/2670/',
    'https://eduon.com/itembank/itemlist/180/2671/',
    'https://eduon.com/itembank/itemlist/180/2692/',
    'https://eduon.com/itembank/itemlist/180/2693/',
    'https://eduon.com/itembank/itemlist/180/2833/',
    'https://eduon.com/itembank/itemlist/180/2835/',
    'https://eduon.com/itembank/itemlist/179/2619/',
    'https://eduon.com/itembank/itemlist/179/2620/',
    'https://eduon.com/itembank/itemlist/179/2621/',
    'https://eduon.com/itembank/itemlist/179/2622/',
    'https://eduon.com/itembank/itemlist/179/2623/',
    'https://eduon.com/itembank/itemlist/179/2624/',
    'https://eduon.com/itembank/itemlist/179/2625/',
    'https://eduon.com/itembank/itemlist/179/2626/',
    'https://eduon.com/itembank/itemlist/179/2627/',
    'https://eduon.com/itembank/itemlist/179/2628/',
    'https://eduon.com/itembank/itemlist/179/2629/',
    'https://eduon.com/itembank/itemlist/179/2630/',
    'https://eduon.com/itembank/itemlist/179/2631/',
    'https://eduon.com/itembank/itemlist/179/2632/',
    'https://eduon.com/itembank/itemlist/179/2633/',
    'https://eduon.com/itembank/itemlist/179/2634/',
    'https://eduon.com/itembank/itemlist/179/2640/',
    'https://eduon.com/itembank/itemlist/179/2641/',
    'https://eduon.com/itembank/itemlist/179/2649/',
    'https://eduon.com/itembank/itemlist/179/2650/',
    'https://eduon.com/itembank/itemlist/179/2836/',
    'https://eduon.com/itembank/itemlist/70/1382/',
    'https://eduon.com/itembank/itemlist/71/1387/',
    'https://eduon.com/itembank/itemlist/70/1383/',
    'https://eduon.com/itembank/itemlist/71/1388/',
    'https://eduon.com/itembank/itemlist/70/1384/',
    'https://eduon.com/itembank/itemlist/71/1389/',
    'https://eduon.com/itembank/itemlist/70/1385/',
    'https://eduon.com/itembank/itemlist/71/1390/',
    'https://eduon.com/itembank/itemlist/70/1386/',
    'https://eduon.com/itembank/itemlist/71/2766/',
    'https://eduon.com/itembank/itemlist/75/1406/',
    'https://eduon.com/itembank/itemlist/76/1407/',
    'https://eduon.com/itembank/itemlist/75/1408/',
    'https://eduon.com/itembank/itemlist/76/1409/',
    'https://eduon.com/itembank/itemlist/75/1410/',
    'https://eduon.com/itembank/itemlist/76/1411/',
    'https://eduon.com/itembank/itemlist/75/1412/',
    'https://eduon.com/itembank/itemlist/76/1413/',
    'https://eduon.com/itembank/itemlist/75/1981/',
    'https://eduon.com/itembank/itemlist/76/1983/',
    'https://eduon.com/itembank/itemlist/75/1982/',
    'https://eduon.com/itembank/itemlist/76/1984/',
    'https://eduon.com/itembank/itemlist/76/2295/',
    'https://eduon.com/itembank/itemlist/75/2296/',
    'https://eduon.com/itembank/itemlist/75/2711/',
    'https://eduon.com/itembank/itemlist/76/2712/',
    'https://eduon.com/itembank/itemlist/55/964/',
    'https://eduon.com/itembank/itemlist/55/965/',
    'https://eduon.com/itembank/itemlist/55/966/',
    'https://eduon.com/itembank/itemlist/55/967/',
    'https://eduon.com/itembank/itemlist/55/968/',
    'https://eduon.com/itembank/itemlist/55/969/',
    'https://eduon.com/itembank/itemlist/55/1036/',
    'https://eduon.com/itembank/itemlist/55/1037/',
    'https://eduon.com/itembank/itemlist/55/1038/',
    'https://eduon.com/itembank/itemlist/55/1039/',
    'https://eduon.com/itembank/itemlist/55/1046/',
    'https://eduon.com/itembank/itemlist/55/1244/',
    'https://eduon.com/itembank/itemlist/55/1356/',
    'https://eduon.com/itembank/itemlist/55/1457/',
    'https://eduon.com/itembank/itemlist/55/1773/',
    'https://eduon.com/itembank/itemlist/55/1774/',
    'https://eduon.com/itembank/itemlist/55/1775/',
    'https://eduon.com/itembank/itemlist/55/1959/',
    'https://eduon.com/itembank/itemlist/55/2045/',
    'https://eduon.com/itembank/itemlist/55/2153/',
    'https://eduon.com/itembank/itemlist/56/970/',
    'https://eduon.com/itembank/itemlist/56/971/',
    'https://eduon.com/itembank/itemlist/56/972/',
    'https://eduon.com/itembank/itemlist/56/973/',
    'https://eduon.com/itembank/itemlist/56/974/',
    'https://eduon.com/itembank/itemlist/56/975/',
    'https://eduon.com/itembank/itemlist/56/1047/',
    'https://eduon.com/itembank/itemlist/56/1048/',
    'https://eduon.com/itembank/itemlist/56/1049/',
    'https://eduon.com/itembank/itemlist/56/1050/',
    'https://eduon.com/itembank/itemlist/56/1051/',
    'https://eduon.com/itembank/itemlist/56/1092/',
    'https://eduon.com/itembank/itemlist/56/1357/',
    'https://eduon.com/itembank/itemlist/56/1456/',
    'https://eduon.com/itembank/itemlist/56/1776/',
    'https://eduon.com/itembank/itemlist/56/1777/',
    'https://eduon.com/itembank/itemlist/56/1778/',
    'https://eduon.com/itembank/itemlist/56/1960/',
    'https://eduon.com/itembank/itemlist/56/2046/',
    'https://eduon.com/itembank/itemlist/56/2152/',
    'https://eduon.com/itembank/itemlist/182/2713/',
    'https://eduon.com/itembank/itemlist/182/2714/',
    'https://eduon.com/itembank/itemlist/182/2716/',
    'https://eduon.com/itembank/itemlist/182/2715/',
    'https://eduon.com/itembank/itemlist/182/2718/',
    'https://eduon.com/itembank/itemlist/182/2719/',
    'https://eduon.com/itembank/itemlist/182/2720/',
    'https://eduon.com/itembank/itemlist/187/2738/',
    'https://eduon.com/itembank/itemlist/187/2739/',
    'https://eduon.com/itembank/itemlist/187/2740/',
    'https://eduon.com/itembank/itemlist/187/2741/',
    'https://eduon.com/itembank/itemlist/187/2742/',
    'https://eduon.com/itembank/itemlist/187/2743/',
    'https://eduon.com/itembank/itemlist/96/1573/',
    'https://eduon.com/itembank/itemlist/96/1574/',
    'https://eduon.com/itembank/itemlist/96/1575/',
    'https://eduon.com/itembank/itemlist/96/1576/',
    'https://eduon.com/itembank/itemlist/96/1578/',
    'https://eduon.com/itembank/itemlist/96/1577/',
    'https://eduon.com/itembank/itemlist/96/1579/',
    'https://eduon.com/itembank/itemlist/96/1580/',
    'https://eduon.com/itembank/itemlist/96/1581/',
    'https://eduon.com/itembank/itemlist/96/1779/',
    'https://eduon.com/itembank/itemlist/96/1780/',
    'https://eduon.com/itembank/itemlist/96/1955/',
    'https://eduon.com/itembank/itemlist/96/2202/',
    'https://eduon.com/itembank/itemlist/96/2210/',
    'https://eduon.com/itembank/itemlist/96/2391/',
    'https://eduon.com/itembank/itemlist/96/2709/',
    'https://eduon.com/itembank/itemlist/96/2804/',
    'https://eduon.com/itembank/itemlist/149/2452/',
    'https://eduon.com/itembank/itemlist/149/2453/',
    'https://eduon.com/itembank/itemlist/149/2454/',
    'https://eduon.com/itembank/itemlist/149/2455/',
    'https://eduon.com/itembank/itemlist/149/2456/',
    'https://eduon.com/itembank/itemlist/149/2457/',
    'https://eduon.com/itembank/itemlist/149/2458/',
    'https://eduon.com/itembank/itemlist/149/2459/',
    'https://eduon.com/itembank/itemlist/149/2460/',
    'https://eduon.com/itembank/itemlist/149/2461/',
    'https://eduon.com/itembank/itemlist/149/2462/',
    'https://eduon.com/itembank/itemlist/149/2463/',
    'https://eduon.com/itembank/itemlist/149/2464/',
    'https://eduon.com/itembank/itemlist/149/2465/',
    'https://eduon.com/itembank/itemlist/149/2466/',
    'https://eduon.com/itembank/itemlist/149/2467/',
    'https://eduon.com/itembank/itemlist/149/2468/',
    'https://eduon.com/itembank/itemlist/149/2469/',
    'https://eduon.com/itembank/itemlist/149/2470/',
    'https://eduon.com/itembank/itemlist/149/2471/',
    'https://eduon.com/itembank/itemlist/149/2472/',
    'https://eduon.com/itembank/itemlist/149/2473/',
    'https://eduon.com/itembank/itemlist/149/2637/',
    'https://eduon.com/itembank/itemlist/149/2763/',
    'https://eduon.com/itembank/itemlist/149/2812/',
    'https://eduon.com/itembank/itemlist/149/2800/'
    ] # 임의 배열

for url in urls:
    fetch_questions(url)