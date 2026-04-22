#!/bin/zsh
# GitHub Secrets 초기 등록 스크립트
# 사전 조건: gh auth login 완료, GitHub 레포 생성 완료
#
# 사용법:
#   chmod +x setup_github.sh
#   ./setup_github.sh

set -e
cd "$(dirname "$0")"

echo "========================================"
echo "  GitHub Secrets 등록"
echo "========================================"
echo ""

# .env 읽기
source .env

# 쿠키 base64 인코딩
COOKIES_B64=$(base64 -i cookies.json)

echo "Secrets 등록 중..."

gh secret set KAKAO_REST_API_KEY   --body "$KAKAO_REST_API_KEY"
gh secret set KAKAO_CLIENT_SECRET  --body "$KAKAO_CLIENT_SECRET"
gh secret set KAKAO_ACCESS_TOKEN   --body "$KAKAO_ACCESS_TOKEN"
gh secret set KAKAO_REFRESH_TOKEN  --body "$KAKAO_REFRESH_TOKEN"
gh secret set ACCOUNT_NUMBER       --body "$ACCOUNT_NUMBER"
gh secret set ACCOUNT_BANK         --body "$ACCOUNT_BANK"
gh secret set ACCOUNT_HOLDER       --body "$ACCOUNT_HOLDER"
gh secret set KAKAO_COOKIES        --body "$COOKIES_B64"

echo ""
echo "GH_PAT (GitHub Personal Access Token)를 입력하세요."
echo "  권한: repo > secrets (write)"
echo "  발급: GitHub → Settings → Developer settings → Personal access tokens"
echo ""
read "GH_PAT?GH_PAT: "
gh secret set GH_PAT --body "$GH_PAT"

echo ""
echo "완료! GitHub Actions가 매주 월요일 08:30에 자동 실행됩니다."
