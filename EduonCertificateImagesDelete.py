import os
import shutil

def delete_images_folders(folder_path):
    for root, dirs, _ in os.walk(folder_path, topdown=False):
        for name in dirs:
            if name == 'images':
                full_path = os.path.join(root, name)
                shutil.rmtree(full_path)
                print(f"Deleted folder: {full_path}")

# '2-4.~~' 폴더의 경로를 지정하세요. 예시 경로는 수정해야 할 수 있습니다.
target_folder_path = 'C:/Users/young/yezy/eduon-crawling/result/2-4. 목표시험구분2 분류 - 과목 포함 - 종목별 과목 분류 최종'

delete_images_folders(target_folder_path)