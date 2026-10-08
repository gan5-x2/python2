from flask import Flask, request
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 上限200MB，可修改

ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "gif", "zip", "rar", "mp4", "md"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# 主页：并行分片上传，保留上传进度条；下载使用浏览器原生链接
@app.route("/")
def index():
    file_list = os.listdir(UPLOAD_FOLDER)
    html = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>高速文件上传下载站</title>
<style>
*{box-sizing:border-box;font-family:"Microsoft Yahei"}
body{max-width:900px;margin:30px auto;padding:0 20px;}
.box{border:1px solid #ccc;padding:24px;border-radius:10px;margin-bottom:20px;}
.progress-wrap{width:100%;height:24px;background:#eee;border-radius:12px;margin:12px 0;overflow:hidden;}
.progress-bar{height:100%;width:0%;background:#2563eb;transition:0.1s;}
.msg{margin:10px 0;padding:10px;border-radius:6px;}
.success{background:#dcfce7;color:#166534}
.error{background:#fee2e2;color:#991b1b}
a{display:block;padding:7px 0;color:#0066cc;text-decoration:none;}
a:hover{color:#e11d48}
#fileInput{margin:10px 0}
</style>
</head>
<body>
<h1>📁 高速文件上传下载站</h1>
<div class="box">
    <h3>📤 文件上传（并行分片上传，带上传进度条）</h3>
    <input type="file" id="fileInput">
    <div class="progress-wrap">
        <div class="progress-bar" id="uploadBar"></div>
    </div>
    <div id="uploadMsg" class="msg"></div>
</div>
<div class="box">
    <h3>📥 文件列表（点击链接下载，浏览器原生下载进度）</h3>
'''
    for fname in file_list:
        html += f'<a href="/download/{fname}">🔗 {fname}</a>'
    html += '''
</div>

<script>
// ========== 并行分片上传 【优化】 ==========
const chunkSize = 10 * 1024 * 1024; // 分片 10MB，局域网可改为20*1024*1024
const maxConcurrent = 3; // 最多同时并发3个分片，不要调太大，容易报错
const uploadBar = document.getElementById("uploadBar");
const uploadMsg = document.getElementById("uploadMsg");

document.getElementById("fileInput").addEventListener("change", async function(e){
    const file = e.target.files[0];
    if(!file) return;
    uploadBar.style.width = "0%";
    uploadMsg.className = "msg";
    uploadMsg.textContent = "开始上传...";
    const totalChunks = Math.ceil(file.size / chunkSize);
    const filename = file.name;

    let finished = 0;
    const queue = [];
    for(let i=0;i<totalChunks;i++) queue.push(i);

    async function worker(){
        while(queue.length>0){
            const idx = queue.shift();
            const start = idx * chunkSize;
            const end = Math.min(start + chunkSize, file.size);
            const chunk = file.slice(start, end);
            const formData = new FormData();
            formData.append("chunk", chunk);
            formData.append("filename", filename);
            formData.append("index", idx);
            formData.append("total", totalChunks);
            await fetch("/upload_chunk", {method:"POST", body:formData});
            finished +=1;
            const percent = ((finished)/totalChunks *100).toFixed(1);
            uploadBar.style.width = percent+"%";
            uploadMsg.textContent = `上传进度 ${percent}%`;
        }
    }
    // 启动多个worker并行上传
    const workers = [];
    for(let w=0;w<maxConcurrent;w++){
        workers.push(worker());
    }
    await Promise.all(workers);

    uploadMsg.className = "msg success";
    uploadMsg.textContent = "✅ 文件上传完成！刷新页面查看文件列表";
});
</script>
</body>
</html>
'''
    return html

# 分片上传接口
@app.route("/upload_chunk", methods=["POST"])
def upload_chunk():
    chunk = request.files["chunk"]
    filename = secure_filename(request.form["filename"])
    idx = int(request.form["index"])
    total = int(request.form["total"])
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    mode = "ab" if idx>0 else "wb"
    with open(save_path, mode) as f:
        f.write(chunk.read())
    return "ok"

# 流式下载接口，加大缓冲区
@app.route("/download/<filename>")
def download(filename):
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    def stream_file():
        with open(filepath, "rb") as f:
            while True:
                chunk = f.read(4 * 1024 * 1024) # 4MB缓冲区读取
                if not chunk:
                    break
                yield chunk
    return app.response_class(
        stream_file(),
        mimetype="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

if __name__ == '__main__':
    # waitress多线程，调高线程池
    from waitress import serve
    print("服务器启动：http://127.0.0.1:5000")
    serve(app, host="127.0.0.1", port=5000, threads=20)
