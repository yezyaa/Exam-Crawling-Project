import os
import openpyxl

def update_image_names_based_on_excel(target_folder_path):
    for subject_folder in os.listdir(target_folder_path):
        subject_path = os.path.join(target_folder_path, subject_folder)
        
        if os.path.isdir(subject_path):
            # 각 종목 폴더 내의 엑셀 파일을 찾아 처리
            for file in os.listdir(subject_path):
                if file.endswith('.xlsx'):
                    excel_path = os.path.join(subject_path, file)
                    workbook = openpyxl.load_workbook(excel_path)
                    sheet = workbook.active
                    
                    # images 폴더 내의 이미지 파일 처리
                    images_folder = os.path.join(subject_path, 'images')
                    if os.path.exists(images_folder):
                        for image in os.listdir(images_folder):
                            image_path = os.path.join(images_folder, image)
                            image_name, image_ext = os.path.splitext(image)
                            # 엑셀 파일의 데이터와 비교하기 위한 준비
                            for row in sheet.iter_rows(min_row=2, values_only=True):
                                excel_file_name = row[0]  # A열: 파일명
                                excel_question_number = row[7]  # H열: 문제번호
                                target_file_name = f"{excel_file_name}_{excel_question_number}"
                                if image_name == target_file_name:
                                    # 새로운 파일명 생성: D열_E열_F열_문제번호
                                    new_image_name = f"{row[3]}_{row[4]}_{row[5]}_{excel_question_number}{image_ext}"
                                    new_image_path = os.path.join(images_folder, new_image_name)
                                    os.rename(image_path, new_image_path)
                                    break  # 일치하는 파일명을 찾았으므로 더 이상의 반복은 필요 없음
                    workbook.close()

# 비교할 폴더 경로 설정
target_folder_path = 'C:/Users/young/yezy/eduon-crawling/result/2-4. 목표시험구분2 분류 - 과목 포함 - 종목별 과목 분류 최종'
update_image_names_based_on_excel(target_folder_path)