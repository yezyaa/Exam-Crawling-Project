import os
import shutil
import openpyxl

def copy_recursively(src, dst):
    if os.path.isdir(src):
        if not os.path.exists(dst):
            os.makedirs(dst)
        items = os.listdir(src)
        for item in items:
            s = os.path.join(src, item)
            d = os.path.join(dst, item)
            if os.path.isdir(s):
                copy_recursively(s, d)
            else:
                shutil.copy2(s, d)
    else:
        shutil.copy2(src, dst)

# 비교 기준 폴더와 비교할 폴더 경로 설정
base_folder_path = 'C:/Users/young/yezy/eduon-crawling/result/2-1. 목표시험구분2 분류 - 과목 포함'
target_folder_path = 'C:/Users/young/yezy/eduon-crawling/result/2-4. 목표시험구분2 분류 - 과목 포함 - 종목별 과목 분류 최종'

# 2-1 폴더의 각 종목 폴더를 순회
for subject_folder in os.listdir(base_folder_path):
    subject_path = os.path.join(base_folder_path, subject_folder)
    
    # 각 종목 폴더 내의 시험 폴더를 순회
    if os.path.isdir(subject_path):
        for exam_folder in os.listdir(subject_path):
            exam_path = os.path.join(subject_path, exam_folder)
            images_folder = os.path.join(exam_path, 'images')
            
            # 시험 폴더 내의 images 폴더가 존재하는 경우
            if os.path.exists(images_folder):
                # 대상 폴더(2-4) 내에 해당 종목 폴더를 찾음
                target_subject_folder = os.path.join(target_folder_path, subject_folder)
                target_images_folder = os.path.join(target_subject_folder, 'images')
                
                # images 폴더와 그 내용을 대상 폴더로 복사
                copy_recursively(images_folder, target_images_folder)
