# GitHub 관리 GUI 앱

macOS 환경에서 GitHub 리포지토리를 관리하기 위한 GUI 애플리케이션입니다.

## 기능

- 리포지토리 목록 조회 및 관리
- 리포지토리 클론/생성/삭제
- 브랜치 관리
- 커밋 히스토리 조회
- Pull Request 관리
- 로컬 CI/CD 기능

## 설치 및 실행

### 요구사항

- Python 3.12 이상
- macOS
- GitHub 개인 액세스 토큰(PAT)

### 설치

```bash
# 저장소 클론
git clone https://github.com/username/project-local-github-repo-manager.git
cd project-local-github-repo-manager

# 의존성 설치
pip install -r requirements.txt

# .env 파일 생성 및 GitHub PAT 설정
echo "GITHUB_PAT=your_github_personal_access_token" > .env
```

### 실행

```bash
python -m gui.main
```

## 개발

### 테스트 실행

```bash
# 모든 테스트 실행
pytest

# 테스트 커버리지 확인
coverage run -m pytest
coverage report
``` 