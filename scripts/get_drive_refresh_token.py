"""Run this ONCE, on your own computer, to connect VibeApp to your Google
Drive - it prints the refresh token you paste into Render's env vars.

Why this script exists: Google service accounts have zero storage quota of
their own and cannot create files in a normal "My Drive" folder (only in a
paid Google Workspace Shared Drive), so VibeApp authenticates as YOUR OWN
Google account instead. That needs a one-time interactive login; this
script does that login and hands you a long-lived refresh token so the
backend never has to ask you to log in again.

Before running this:
  1. console.cloud.google.com -> your project -> APIs & Services ->
     Credentials -> Create Credentials -> OAuth client ID.
  2. Application type: "Desktop app". Name it anything (e.g. "VibeApp CLI").
  3. Download the JSON it gives you, save it next to this script as
     client_secret.json (or pass its path as an argument - see below).

Usage (from the backend/ folder):

    pip install google-auth-oauthlib
    python scripts/get_drive_refresh_token.py [path/to/client_secret.json]

A browser tab opens - log in with the SAME Google account whose Drive you
want VibeApp to use, and approve access. The script then prints your
GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET, and
GOOGLE_OAUTH_REFRESH_TOKEN - copy all three into Render's Environment tab,
alongside GOOGLE_DRIVE_FOLDER_ID (the folder you want files uploaded into,
its ID from the folder's URL on drive.google.com).

Note: google-auth-oauthlib is ONLY needed to run this script locally - it is
deliberately NOT in backend/requirements.txt, since the deployed backend
itself only needs google-auth (already a dependency) to use the refresh
token this script produces.
"""

import sys
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/drive"]


def main():
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print(
            "Thiếu thư viện google-auth-oauthlib. Chạy trước:\n"
            "    pip install google-auth-oauthlib\n"
            "rồi chạy lại script này.",
            file=sys.stderr,
        )
        sys.exit(1)

    client_secret_path = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        Path(__file__).parent / "client_secret.json"
    )
    if not client_secret_path.exists():
        print(
            f"Không thấy file: {client_secret_path}\n"
            "Tải file JSON của OAuth Client ID (loại \"Desktop app\") từ "
            "Google Cloud Console -> Credentials, đặt cạnh script này với tên "
            "client_secret.json, hoặc truyền đường dẫn làm tham số:\n"
            "    python scripts/get_drive_refresh_token.py duong/dan/file.json",
            file=sys.stderr,
        )
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_path), SCOPES)
    # access_type=offline (mặc định của InstalledAppFlow) + prompt=consent để
    # LUÔN nhận được refresh_token, kể cả khi tài khoản này đã từng đồng ý
    # trước đó (Google chỉ trả refresh_token ở lần consent đầu tiên nếu không
    # ép prompt=consent).
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

    if not creds.refresh_token:
        print(
            "Không nhận được refresh_token từ Google. Thường do tài khoản này "
            "đã từng cấp quyền trước đó - vào myaccount.google.com/permissions, "
            "gỡ quyền truy cập của app này, rồi chạy lại script.",
            file=sys.stderr,
        )
        sys.exit(1)

    print("\nThành công! Dán 3 dòng dưới vào Render -> Environment "
          "(kèm GOOGLE_DRIVE_FOLDER_ID của thư mục Drive anh muốn dùng):\n")
    print(f"GOOGLE_OAUTH_CLIENT_ID={creds.client_id}")
    print(f"GOOGLE_OAUTH_CLIENT_SECRET={creds.client_secret}")
    print(f"GOOGLE_OAUTH_REFRESH_TOKEN={creds.refresh_token}")
    print(
        "\nGiữ 3 giá trị này cẩn thận, không chia sẻ công khai - ai có "
        "refresh token này upload/xóa được file trong Drive của tài khoản anh."
    )


if __name__ == "__main__":
    main()
