import os
import pandas as pd

# 공인중개사 최상위 폴더 경로
top_folder_path = 'C:/Users/young/yezy/eduon-crawling/result/PC정비사 2급'

# 최종 데이터를 저장할 빈 DataFrame 생성
all_data = pd.DataFrame()

# 최상위 폴더 내의 모든 시험 폴더를 순회
for folder_name in os.listdir(top_folder_path):
    exam_folder_path = os.path.join(top_folder_path, folder_name)
    
    # 시험 폴더 내의 모든 파일을 순회
    for file_name in os.listdir(exam_folder_path):
        if file_name.endswith('.xlsx'):
            excel_file_path = os.path.join(exam_folder_path, file_name)
            
            # 엑셀 파일 읽기
            df = pd.read_excel(excel_file_path)
            
            # 파일명에서 '.xlsx' 확장자 제거
            file_name_without_extension = file_name.replace('.xlsx', '')
            
            # '파일명' 열 추가 - 각 행에 현재 엑셀 파일 이름(확장자 제외)을 삽입
            df['파일명'] = file_name_without_extension
            
            # 데이터를 all_data DataFrame에 추가
            all_data = pd.concat([all_data, df], ignore_index=True)

# 모든 데이터를 합친 후, '파일명' 열을 첫 번째 열로 만들기 위한 열 순서 조정
cols = ['파일명'] + [col for col in all_data.columns if col != '파일명']
all_data = all_data[cols]

# 모든 데이터가 담긴 DataFrame을 새로운 엑셀 파일로 저장
output_file_path = os.path.join(top_folder_path, 'PC정비사 2급.xlsx')
all_data.to_excel(output_file_path, index=False)