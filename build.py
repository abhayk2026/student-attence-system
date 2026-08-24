import os
import zipfile

def build_project():
    print("🚀 Initializing AI Weather Project Builder...")
    
    project_files = {
        "weather_ai_project/requirements.txt": "fastapi==0.110.1\nuvicorn==0.29.0\npython-multipart==0.0.9\npandas==2.2.1\nnumpy==1.26.4\nscikit-learn==1.4.1.post1\njoblib==1.3.2\ngoogle-generativeai==0.4.1\nSQLAlchemy==2.0.29\npython-dotenv==1.0.1\nrequests==2.31.0\npytest==8.1.1\n",
        "weather_ai_project/.env.example": "GEMINI_API_KEY=your_gemini_api_key_here\nWEATHER_API_KEY=your_weather_api_key_here\nDATABASE_URL=sqlite:///./weather_app.db\n",
        "weather_ai_project/README.md": "# AI-Based Weather Prediction Project\n1. Run `python -m venv venv` and activate it.\n2. Run `pip install -r requirements.txt`.\n3. Create `.env` from `.env.example` and add Gemini API key.\n4. Generate Data: `python data/generate_dataset.py`\n5. Train Model: `python models/train_model.py`\n6. Start App: `python app.py`\n"
    }

    # 1. Create files locally
    print("📁 Creating directories and writing files...")
    for file_path, content in project_files.items():
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    # 2. Package into a ZIP file
    print("📦 Compressing into 'weather_ai_project.zip'...")
    with zipfile.ZipFile("weather_ai_project.zip", "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk("weather_ai_project"):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, "."))
                    
    print("\n✅ SUCCESS! Project successfully generated.")

if __name__ == "__main__":
    build_project()