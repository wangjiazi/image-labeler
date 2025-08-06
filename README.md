# Image Label Tool

1. Download `images.zip` from  https://huggingface.co/datasets/Wendy-Fly/Vases-Agent/tree/main and unzip to '/images'
```bash
unzip -o images.zip -d images/
```

2. Replace all `.jpe` extensions with `.jpg` in the `images` directory. You can run the following command in the `images` folder (Linux/macOS):
 > This step may take a few minutes.
```bash
cd images
for f in *.jpe; do mv -- "$f" "${f%.jpe}.jpg"; done
cd ..
```

3. Installation environment (preferably in a conda virtual environment)
```bash
pip install -r requirements.txt
```

4. Run the annotation interface and select a task to annotate
```bash
python image_labeler.py
```

5. Select your task and label
