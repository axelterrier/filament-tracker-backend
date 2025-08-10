# 🧠 Filament Tracker Backend

Backend service for the **Filament Tracker** project.  
This API allows you to track and manage your 3D printing filament inventory.

Works together with the frontend available here:  
👉 https://github.com/axelterrier/filament-tracker-frontend

---

## 📖 Description

The Filament Tracker backend provides a REST API to:
- Add, edit, and remove filament spools manually
- Sync filament data automatically from a **Bambu Lab AMS** (LAN mode)
- Import Bambulab filament details from **Proxmark** RFID tag scans

---

## 🚀 Getting Started

### 📋 Prerequisites
- Python 3.9+
- pip (Python package manager)

### 📥 Installation
Clone the repository:
```bash
git clone https://github.com/axelterrier/filament-tracker-backend.git
cd filament-tracker-backend
```

Install dependencies:
```bash
pip install -r requirements.txt
```

### ▶️ Running the Server
```bash
python app.py
```
By default, the API will be available at:  
`http://localhost:5000`

---

## ⚙️ Features for Bambu Lab Users
- **AMS Sync**: Retrieve real-time filament data from your AMS (LAN mode required)
- **RFID Import**: Use a Proxmark reader to import spool details directly from filament tags

---

## 🤝 Contributing
Contributions are welcome!  
1. Fork the repository  
2. Create a branch (`git checkout -b feature/my-feature`)  
3. Commit your changes  
4. Push to your fork  
5. Open a Pull Request

---

## 📜 License
This project does not currently specify a license.
