import os
import openpyxl
from pathlib import Path

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
                    
                    # 이미지 폴더 경로 설정
                    images_folder_path = os.path.join(subject_path, 'images')
                    if not os.path.exists(images_folder_path):
                        print(f"No images folder found for {subject_folder}")
                        continue

                    # 엑셀 파일 내의 모든 행을 순회하면서 이미지 파일 이름 변경
                    for row in sheet.iter_rows(min_row=2, values_only=True):
                        old_name_prefix, question_number, new_prefix = str(row[0]), str(row[7]), f"{row[3]}_{row[4]}_{row[5]}"
                        # images 폴더 및 하위 폴더 내의 파일 이름 변경
                        for root, dirs, files in os.walk(images_folder_path):
                            for filename in files:
                                if filename.startswith(old_name_prefix) and question_number in filename:
                                    new_name = filename.replace(old_name_prefix, new_prefix, 1)
                                    original_path = os.path.join(root, filename)
                                    new_path = os.path.join(root, new_name)
                                    try:
                                        os.rename(original_path, new_path)
                                        print(f"Renamed {original_path} to {new_path}")
                                    except Exception as e:
                                        print(f"Error renaming {original_path} to {new_path}: {e}")

# 최상위 폴더 경로 설정 (예시 경로를 실제 경로로 변경해주세요)
target_folder_path = 'C:/Users/young/yezy/eduon-crawling/result/2-4. 목표시험구분2 분류 - 과목 포함 - 종목별 과목 분류 최종'
update_image_names_based_on_excel(target_folder_path)
