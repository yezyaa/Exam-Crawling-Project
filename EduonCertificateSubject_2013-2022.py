import pandas as pd
import os

# 결과 저장 폴더 및 소스 엑셀 파일 경로 설정
source_folder = 'C:/Users/young/yezy/eduon-crawling/result/2-2. 목표시험구분2 분류 - 과목 포함 - 종목 합치기'
output_folder = 'C:/Users/young/yezy/eduon-crawling/result/2-4. 목표시험구분2 분류 - 과목 포함 - 종목별 과목 분류 최종'

# 결과 저장 폴더 생성 (이미 존재하지 않는 경우)
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# 지정된 폴더 내의 엑셀 파일을 순회하며 과목별로 데이터 분류 및 저장
for filename in os.listdir(source_folder):
    if filename.endswith('.xlsx'):
        # 원본 파일 경로
        file_path = os.path.join(source_folder, filename)
        
        # 엑셀 파일 읽기
        df = pd.read_excel(file_path, engine='openpyxl')

        # 과목명에서 '/' 문자를 '-'로 변경
        df['과목'] = df['과목'].apply(lambda x: x.replace('/', '_'))
        
        # 컬럼명 변경
        df.rename(columns={
            'Info_1': '수험분야',
            'Info_2': '목표시험구분1',
            'Info_3': '목표시험구분2',
            'Info_4': '시행연도',
            'Info_5': '시행차수',
        }, inplace=True)

        # '목표시험구분1' 컬럼에 '필기'로 값 채우기
        df['목표시험구분1'] = '필기'
        
        # 과목별 데이터를 저장할 딕셔너리 초기화
        subjects_dfs = {}
        
        # 데이터 분류
        for _, row in df.iterrows():
            subject = row['과목']
            if subject not in subjects_dfs:
                subjects_dfs[subject] = []
            subjects_dfs[subject].append(row)

        # 각 과목별로 새로운 엑셀 파일 생성 및 저장
        for subject, rows in subjects_dfs.items():
            subject_df = pd.DataFrame(rows)
            # 컬럼 삭제 처리
            subject_df.drop(['과목', '문제.1', '지문', '보기'], axis=1, errors='ignore', inplace=True)
            
            # F열부터 J열까지의 데이터를 A열 바로 뒤로 이동
            cols = subject_df.columns.tolist()  # 현재 컬럼 순서를 가져옴
            
            # 새로운 컬럼 순서 정의
            new_order = cols[0:1] + cols[5:10] + cols[1:5] + cols[10:]
            subject_df = subject_df[new_order]

            # 책형 컬럼 추가
            subject_df.insert(loc=6, column='책형', value="")  # 시행차수(F열) 오른쪽에 책형 컬럼 추가

            # 문제변경일 컬럼 추가
            subject_df.insert(loc=9, column='문제변경일', value="")  # 문제(I열) 오른쪽에 책형 컬럼 추가
            
            # 목표시험구분2 값에서 특수 문자를 '-'로 대체
            exam_name = subject_df['목표시험구분2'].iloc[0]  # 첫 번째 데이터의 목표시험구분2 사용
            for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
                exam_name = exam_name.replace(char, '_')
            
            # 새로운 폴더 생성 로직
            new_folder = os.path.join(output_folder, exam_name)
            if not os.path.exists(new_folder):
                os.makedirs(new_folder, exist_ok=True)

            # 파일명 설정 및 저장
            output_file = os.path.join(new_folder, f'{exam_name} - {subject} 2013~2022 - 이예지.xlsx')
            subject_df.to_excel(output_file, index=False)