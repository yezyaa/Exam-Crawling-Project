from requests_html import HTMLSession
import re
from bs4 import BeautifulSoup
import os
import requests

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
def fetch_questions(url):
    session = HTMLSession()
    response = session.get(url)
    response.html.render()

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

# 문제 컨텐츠 추출
def extract_question(question):
    global base_url

    # 문제
    question_text_elem = question.find('strong', class_='question')
    
    # 문제 번호
    question_number_elem = question_text_elem.find('span')
    if question_number_elem:
        question_number = question_number_elem.text
    else:
        question_number = ""    

    # 문제 번호가 1자리인 경우
    if question_number.isdigit() and len(question_number) == 1:
        question_text_elem.find('span').extract()
        question_number = question_number_elem.text

    question_text = question_text_elem.get_text(strip=True)

    # 문제에 번호 넘어가는 현상 제거
    if question_number and question_number[:2] == question_text[:2]:
        question_text = question_text[2:].strip()

    # 보기
    viewbox_elem = question.find('div', class_='viewbox')
    if viewbox_elem:
        for u_tag in viewbox_elem.find_all('u'):
            u_tag.replace_with(f"<u>{u_tag.text}</u>")
        viewbox_content = viewbox_elem.get_text(strip=True)
    else:
        viewbox_content = "보기 X"

    # 정답
    correct_answer_elem = question.find('li', class_='viewCorrect')
    correct_answer = correct_answer_elem.get_text(strip=True)[0].replace('①', '1').replace('②', '2').replace('③', '3').replace('④', '4').replace('⑤', '5') if correct_answer_elem else "정답 X"

    # 출처
    ref_elem = question.find('span', class_='ref')
    reference = ref_elem.get_text(strip=True) if ref_elem else "출처 X"

    # 해설
    explanation_elem = question.find('div', class_='q-text view_explanation')
    explanation = explanation_elem.get_text(strip=True) if explanation_elem else "해설 정보 X"

    # 문제 번호 추출
    print(f"\n번호\n{question_number}")

    # 문제 추출
    print(f"\n문제\n{question_text}")

    # 지문 추출
    print("\n지문")  # "지문" 타이틀은 무조건 출력
    viewbox_elem = question.find('div', class_='viewbox')
    if viewbox_elem:
        images = viewbox_elem.find_all('img')
        text_content = viewbox_elem.get_text(strip=True)
        if images:  # 이미지가 있는 경우
            for img in images:
                img_src = base_url + img['src']
                # print("이미지")
                download_image(img_src, question_number, reference)
        if text_content.strip():  # 텍스트 내용이 있는 경우에만 텍스트 출력
            print(text_content.strip())
        # 이미지가 있으나 텍스트 내용이 없는 경우 이미지는 다운로드 되지만, 여기서 별도의 출력은 하지 않음

    # 보기 추출
    choices_elem = question.find('div', class_='sel-answer')
    for u_tag in choices_elem.find_all('u'):
        u_tag.replace_with(f"<u>{u_tag.text}</u>")

    if choices_elem:
        # Handle list format choices
        if choices_elem.find('ul', class_='radio_qb'):
            choices_list = choices_elem.find_all('li')
            print("\n보기")
            for index, choice in enumerate(choices_list, 1):
                choice_text = choice.get_text(strip=True).replace('①', '1.').replace('②', '2.').replace('③', '3.').replace('④', '4.').replace('⑤', '5.')
                print(f"{choice_text}")

        # Handle table format choices
        elif choices_elem.find('table', class_='table_answer'):
            table = choices_elem.find('table')
            rows = table.find_all('tr')

            # Extract headers from the first row
            headers = [th.get_text(strip=True) for th in rows[0].find_all('th')]

            print("\n보기")
            for row in rows[1:]:  # Skip header row
                cells = row.find_all('td')
                choice_prefix = cells[0].get_text(strip=True)  # Get the choice number (e.g., ①, ②)

                # Adjusting for the correct number of cells to match with headers
                cell_data = cells[1:len(headers) + 1]  # Adjust the range to match the number of headers

                formatted_row = ' '.join(
                    [f"{headers[i]} {cell.get_text(strip=True)}" for i, cell in enumerate(cell_data)])
                print(f"{choice_prefix} {formatted_row}")

    # 정답 추출
    print("\n정답\n", correct_answer)
    # print("출처 ", reference)

    # 해설 추출
    print("\n해설")  # "해설" 타이틀은 무조건 출력
    explanation_elem = question.find('div', class_='q-text view_explanation')
    if explanation_elem:
        explanation_images = explanation_elem.find_all('img')
        explanation_text = explanation_elem.get_text(strip=True)
        if explanation_images:  # 해설 섹션에 이미지가 있는 경우
            for img in explanation_images:
                img_src = base_url + img['src']
                # 이미지 다운로드 관련 로직은 실제로 여기서 호출됩니다.
                download_image(img_src, question_number, reference, is_explanation=True)
        if explanation_text.strip():  # 해설 텍스트 내용이 있는 경우에만 텍스트 출력
            print(explanation_text.strip())
        # 이미지가 있으나 텍스트 내용이 없는 경우 이미지는 다운로드 되지만, 여기서 별도의 출력은 하지 않음

    # 해설 섹션 이미지 처리
    explanation_elem = question.find('div', class_='q-text view_explanation')
    if explanation_elem:
        explanation_images = explanation_elem.find_all('img')
        for img in explanation_images:
            img_src = base_url + img['src']
            download_image(img_src, question_number, reference, is_explanation=True)

# 이미지 다운로드 및 저장
def download_image(img_url, question_number, reference, is_explanation=False):
    try:
        clean_reference = re.sub(r'[()]', '', reference).strip()
        directory_path = "images/" + clean_reference + ("/해설" if is_explanation else "")
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)

        response = requests.get(img_url)
        file_extension = img_url.split(".")[-1]
        filename_prefix = "_해설" if is_explanation else ""
        filename = f"{directory_path}/{clean_reference}{filename_prefix}_{question_number}.{file_extension}"
        with open(filename, "wb") as f:
            f.write(response.content)
        # print(f"이미지 다운로드 완료: {filename}")
    except Exception as e:
        print(f"이미지 다운로드 오류: {e}")

# URL 설정
base_url = 'https://eduon.com/'
urls = ['https://eduon.com/itembank/itemlist/11/777/'] # 임의 배열

for url in urls:
    fetch_questions(url)