from requests_html import HTMLSession
from bs4 import BeautifulSoup
import re
import os
import requests
import pandas as pd    

# 여러 개의 주소 배열 받기 위한 준비
def modify_url(original_url):
    # URL에서 숫자 부분을 추출
    numbers = re.findall(r'\d+', original_url)

    if len(numbers) < 2:
        raise ValueError("URL에 필요한 숫자 부분이 존재하지 않습니다.")
    # 새로운 URL 구성
    new_url = f"https://eduon.com/itembank/ajax_itemlist/{numbers[0]}/{numbers[1]}/"
    return new_url

# 마지막 페이지까지 문제 전체 가져오기
def fetch_questions(url, clear_list=True):
    session = HTMLSession()
    response = session.get(url)
    response.html.render()

    global all_questions
    if clear_list:
        all_questions = []

    # 마지막 페이지 번호 찾기
    page_links = response.html.find('a.page-link')
    page_numbers = [int(re.search(r'\d+', link.text).group()) for link in page_links if re.search(r'\d+', link.text)]
    max_page = max(page_numbers, default = 1)

    # 모든 페이지를 순회하면서 문제 목록 추출
    for page in range(1, max_page + 1):
        # 페이지 번호에 따른 요청 URL 설정
        page_url = modify_url(url)

        # 페이지 번호를 payload로 설정
        payload = {'hj_check': '', 'npg': page, 'stext': '', 'cp': ''}

        # 페이지 데이터 가져오기
        response = session.get(page_url, params=payload)
        soup = BeautifulSoup(response.content, 'html.parser')

        # 문제 목록 추출
        questions = soup.find_all('div', class_='qb_question')
        for question in questions:
            extract_question(question)

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

# 컨텐츠 최종 출력
def extract_question(question):
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
    question_data = [question_number, question_text, viewbox_text, choices_text, correct_answer, explanation_text]
    all_questions.append(question_data)

    # 데이터프레임 생성 및 엑셀 파일로 저장
    df = pd.DataFrame(all_questions, columns=['번호', '문제', '지문', '보기', '정답', '해설'])
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
    ] # 임의 배열

for url in urls:
    fetch_questions(url)