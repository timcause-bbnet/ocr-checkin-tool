# OCR 證件辨識系統 (OCR Document Recognition)

這是一個基於 Python Streamlit 的網頁應用程式，專門用於辨識台灣身分證及各國護照的關鍵資訊，並自動整理成入住登記所需的格式。

## ✨ 主要功能 (Features)

*   **台灣身分證辨識**：
    *   自動抓取姓名、身分證字號、出生年月日 (自動轉西元)、地址。
    *   支援正反面辨識。
*   **各國護照辨識 (Passport MRZ)**：
    *   支援所有標準 MRZ (機器可讀區) 的護照。
    *   **特別優化**：針對 中國 (CHN)、台灣 (TWN)、德國 (DEU)、日本 (JPN)、南韓 (KOR)、泰國 (THA) 等國護照進行邏輯校正。
    *   **容錯處理**：自動修正 OCR 常見錯誤 (如數字 0 與字母 O 混淆)。
*   **自動填表**：
    *   將辨識後的雜亂資訊標準化為「姓名」、「生日」、「國籍」、「證件號碼」、「性別」等標準欄位。
*   **手機與 Web 支援**：
    *   支援手機拍照上傳或直接開啟相機。
    *   RWD 響應式介面。

## 🛠️ 安裝與執行 (Installation & Usage)

### 1. 環境需求
*   Python 3.8 或以上版本。
*   Windows / Mac / Linux 皆可執行。

### 2. 快速啟動 (Windows)
直接點擊目錄下的 **`run_ocr.bat`** 即可自動安裝套件並啟動網頁。

### 3. 手動安裝與執行
若您習慣使用指令列：

```bash
# 安裝相依套件
pip install -r requirements.txt

# 啟動應用程式
streamlit run app.py
```

### 4. 區域網路連線
啟動後，程式會顯示兩組網址：
*   **Local URL**: `http://localhost:8501` (本機使用)
*   **Network URL**: `http://192.168.x.x:8501` (同一 WiFi 下的手機可連此網址使用)

## 📂 專案結構
*   `app.py`: Streamlit 網頁主程式。
*   `ocr_utils.py`: 核心 OCR 辨識邏輯與 MRZ 解析演算法。
*   `requirements.txt`: Python 套件需求清單。
*   `packages.txt`: 系統層級相依套件 (如 Linux 部署需用到)。
*   `run_ocr.bat`: Windows 一鍵啟動腳本。
*   `.github/workflows/`: GitHub Actions 自動化部署設定。

## 🚀 部署 (Deployment)
本專案包含 **Dockerfile**，您可以將其打包為 Docker Image 並部署至任何支援 Docker 的雲端平台 (如 Azure App Service, AWS ECS, Google Cloud Run) 或使用 GitHub Actions 自動建置。

```bash
# 建置 Docker Image
docker build -t ocr-app .

# 執行 Container
docker run -p 8501:8501 ocr-app
```
