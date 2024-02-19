import os
import pandas as pd

# eduon-certificate_2013-2022.xlsx 파일 로드
reference_path = 'C:/Users/young/yezy/eduon-crawling/result/eduon-certificate_2013-2022.xlsx'
reference_df = pd.read_excel(reference_path)

# 최상위 폴더 경로
top_folder_path = 'C:/Users/young/yezy/eduon-crawling/result'

# 결과 저장 디렉터리 확인 및 생성
output_directory = top_folder_path
if not os.path.exists(output_directory):
    os.makedirs(output_directory)

# 최상위 폴더 내의 모든 하위 폴더를 순회
for folder_name in os.listdir(top_folder_path):
    folder_path = os.path.join(top_folder_path, folder_name)
    
    # 폴더인지 확인
    if os.path.isdir(folder_path):
        all_data = pd.DataFrame()  # 폴더별 합친 데이터를 저장할 DataFrame
        
        # 시험 폴더 내의 모든 엑셀 파일을 순회
        for file_name in os.listdir(folder_path):
            if file_name.endswith('.xlsx') and file_name != 'eduon-certificate_2013-2022.xlsx':
                file_path = os.path.join(folder_path, file_name)
                df = pd.read_excel(file_path)
                
                # A열(파일명)을 기준으로 정보 추가
                for index, row in df.iterrows():
                    file_title = row.iloc[0]  # 가정: A열에 파일명이 있다고 가정
                    match = reference_df[reference_df.iloc[:, 0] == file_title]  # A열에서 일치하는 행 찾기
                    
                    if not match.empty:
                        # B열부터 F열까지의 정보를 현재 행에 추가
                        for col_idx in range(1, 6):  # B열(1)부터 F열(5)까지
                            df.loc[index, f'Info_{col_idx}'] = match.iloc[0, col_idx]
                
                # 폴더별 합친 데이터에 추가
                all_data = pd.concat([all_data, df], ignore_index=True)
        
        if not all_data.empty:
            # 수정된 DataFrame을 새로운 엑셀 파일로 저장
            output_path = os.path.join(output_directory, f'{folder_name}.xlsx')
            all_data.to_excel(output_path, index=False)

            print(f'{folder_name}.xlsx 파일이 성공적으로 생성되었습니다.')
