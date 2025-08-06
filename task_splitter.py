 #!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务分割工具
将图片分割成多个任务包，用于多人协作标注
"""

import os
import json
import shutil
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from datetime import datetime
import random

class TaskSplitter:
    def __init__(self, root):
        self.root = root
        self.root.title("Task splitter")
        self.root.geometry("800x600")
        self.root.configure(bg='#f0f0f0')
        
        # 设置项目路径
        self.project_dir = Path(__file__).parent
        self.images_dir = self.project_dir / "images"  # 默认图片目录
        self.tasks_dir = self.project_dir / "tasks"
        
        # 创建tasks目录
        self.tasks_dir.mkdir(exist_ok=True)
        
        # 初始化变量
        self.image_files = []
        self.task_size = tk.IntVar(value=50)  # 默认每个任务50张图片
        self.shuffle_images = tk.BooleanVar(value=True)  # 默认随机打乱
        
        # 创建界面
        self.create_widgets()
        
        # 扫描图片
        self.scan_images()
    
    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # 标题
        title_label = ttk.Label(main_frame, text="Task splitter", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # 图片目录信息
        dir_frame = ttk.LabelFrame(main_frame, text="Image directory", padding="10")
        dir_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 目录选择区域
        dir_select_frame = ttk.Frame(dir_frame)
        dir_select_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Label(dir_select_frame, text="Image directory:").grid(row=0, column=0, sticky=tk.W)
        self.dir_label = ttk.Label(dir_select_frame, text=str(self.images_dir), 
                                  font=('Arial', 9), foreground='blue')
        self.dir_label.grid(row=0, column=1, padx=(10, 10), sticky=(tk.W, tk.E))
        
        # 选择目录按钮
        select_dir_button = ttk.Button(dir_select_frame, text="Select directory", 
                                     command=self.select_images_directory)
        select_dir_button.grid(row=0, column=2, padx=(0, 10))
        
        # 扫描按钮
        scan_button = ttk.Button(dir_select_frame, text="Re-scan images", command=self.scan_images)
        scan_button.grid(row=0, column=3, padx=(0, 0))
        
        # 图片统计信息
        self.stats_label = ttk.Label(dir_frame, text="", font=('Arial', 9))
        self.stats_label.grid(row=1, column=0, columnspan=3, pady=(5, 0))
        
        # 任务配置
        config_frame = ttk.LabelFrame(main_frame, text="Task configuration", padding="10")
        config_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 每个任务的图片数量
        ttk.Label(config_frame, text="Image count per task:").grid(row=0, column=0, sticky=tk.W)
        task_size_spinbox = ttk.Spinbox(config_frame, from_=10, to=200, width=10, 
                                       textvariable=self.task_size)
        task_size_spinbox.grid(row=0, column=1, padx=(10, 0), sticky=tk.W)
        
        # 随机打乱选项
        shuffle_check = ttk.Checkbutton(config_frame, text="Shuffle image order", 
                                      variable=self.shuffle_images)
        shuffle_check.grid(row=1, column=0, columnspan=2, pady=(5, 0), sticky=tk.W)
        
        # 任务预览
        preview_frame = ttk.LabelFrame(main_frame, text="Task preview", padding="10")
        preview_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        
        # 预览文本框
        self.preview_text = tk.Text(preview_frame, height=10, width=80)
        preview_scrollbar = ttk.Scrollbar(preview_frame, orient="vertical", command=self.preview_text.yview)
        self.preview_text.configure(yscrollcommand=preview_scrollbar.set)
        
        self.preview_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        preview_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=20)
        
        # 预览按钮
        preview_button = ttk.Button(button_frame, text="Preview task split", 
                                  command=self.preview_tasks)
        preview_button.grid(row=0, column=0, padx=10)
        
        # 生成任务按钮
        self.generate_button = ttk.Button(button_frame, text="Generate task files", 
                                        command=self.generate_tasks)
        self.generate_button.grid(row=0, column=1, padx=10)
        
        # 清理任务按钮
        clear_button = ttk.Button(button_frame, text="Clear all tasks", 
                                command=self.clear_all_tasks)
        clear_button.grid(row=0, column=2, padx=10)
        
        # 状态栏
        self.status_label = ttk.Label(main_frame, text="", font=('Arial', 9))
        self.status_label.grid(row=5, column=0, columnspan=2, pady=(10, 0))
    
    def scan_images(self):
        """扫描图片文件"""
        if not self.images_dir.exists():
            messagebox.showerror("Error", f"Image directory does not exist: {self.images_dir}")
            return
        
        # 获取所有图片文件
        image_extensions = {'.jpg', '.jpeg', '.jpe', '.png', '.bmp', '.gif', '.tiff'}
        self.image_files = []
        
        for file_path in self.images_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                self.image_files.append(file_path)
        
        self.image_files.sort()  # 按文件名排序
        self.update_stats_display()
        self.update_status(f"Scan completed, found {len(self.image_files)} images")
    
    def select_images_directory(self):
        """选择图片目录"""
        directory = filedialog.askdirectory(
            title="Select image directory",
            initialdir=str(self.images_dir) if self.images_dir.exists() else str(self.project_dir)
        )
        
        if directory:
            self.images_dir = Path(directory)
            self.dir_label.configure(text=str(self.images_dir))
            self.update_status(f"Selected image directory: {self.images_dir}")
            
            # 自动扫描新目录
            self.scan_images()
    
    def update_stats_display(self):
        """更新统计信息显示"""
        if self.image_files:
            stats_text = f"Found {len(self.image_files)} images"
            if self.task_size.get() > 0:
                task_count = (len(self.image_files) + self.task_size.get() - 1) // self.task_size.get()
                stats_text += f" | Will generate {task_count} task files"
        else:
            stats_text = "No image files found"
        
        self.stats_label.configure(text=stats_text)
    
    def preview_tasks(self):
        """预览任务分割"""
        if not self.image_files:
            messagebox.showwarning("Warning", "No image files to split")
            return
        
        # 清空预览
        self.preview_text.delete(1.0, tk.END)
        
        # 准备图片列表
        image_list = self.image_files.copy()
        if self.shuffle_images.get():
            random.shuffle(image_list)
        
        # 计算任务数量
        task_size = self.task_size.get()
        if task_size <= 0:
            messagebox.showerror("Error", "Task size must be greater than 0")
            return
        
        task_count = (len(image_list) + task_size - 1) // task_size
        
        # 生成预览
        preview_text = f"Task split preview:\n"
        preview_text += f"Total image count: {len(image_list)}\n"
        preview_text += f"Image count per task: {task_size}\n"
        preview_text += f"Task file count: {task_count}\n"
        preview_text += f"Shuffle: {'Yes' if self.shuffle_images.get() else 'No'}\n"
        preview_text += "=" * 50 + "\n\n"
        
        for i in range(task_count):
            start_idx = i * task_size
            end_idx = min(start_idx + task_size, len(image_list))
            task_images = image_list[start_idx:end_idx]
            
            preview_text += f"Task {i+1}:\n"
            preview_text += f"  Image count: {len(task_images)}\n"
            preview_text += f"  Image list:\n"
            for j, img_path in enumerate(task_images, 1):
                preview_text += f"    {j:2d}. {img_path.name}\n"
            preview_text += "\n"
        
        self.preview_text.insert(1.0, preview_text)
        self.update_status("Preview generated")
    
    def generate_tasks(self):
        """生成任务包"""
        if not self.image_files:
            messagebox.showwarning("Warning", "No image files to split")
            return
        
        try:
            # 准备图片列表
            image_list = self.image_files.copy()
            if self.shuffle_images.get():
                random.shuffle(image_list)
            
            # 计算任务数量
            task_size = self.task_size.get()
            if task_size <= 0:
                messagebox.showerror("Error", "Task size must be greater than 0")
                return
            
            task_count = (len(image_list) + task_size - 1) // task_size
            
            # 生成时间戳
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 创建任务包
            created_tasks = []
            for i in range(task_count):
                start_idx = i * task_size
                end_idx = min(start_idx + task_size, len(image_list))
                task_images = image_list[start_idx:end_idx]
                
                # 创建任务数据
                task_data = {
                    "task_id": f"task_{timestamp}_{i+1:03d}",
                    "task_name": f"Task {i+1}",
                    "created_time": datetime.now().isoformat(),
                    "total_images": len(task_images),
                    "images": [img.name for img in task_images],
                    "status": "pending",  # pending, in_progress, completed
                    "progress": {
                        "highQuality": 0,
                        "lowQuality": 0,
                        "skip": 0,
                        "total": len(task_images)
                    }
                }
                
                # 保存任务文件
                task_filename = f"task_{timestamp}_{i+1:03d}.json"
                task_path = self.tasks_dir / task_filename
                
                with open(task_path, 'w', encoding='utf-8') as f:
                    json.dump(task_data, f, ensure_ascii=False, indent=2)
                
                created_tasks.append(task_filename)
            
            # 生成任务索引文件
            index_data = {
                "batch_id": timestamp,
                "created_time": datetime.now().isoformat(),
                "total_tasks": task_count,
                "total_images": len(image_list),
                "task_size": task_size,
                "shuffled": self.shuffle_images.get(),
                "tasks": created_tasks
            }
            
            index_filename = f"batch_{timestamp}.json"
            index_path = self.tasks_dir / index_filename
            
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, ensure_ascii=False, indent=2)
            
            messagebox.showinfo("Success", 
                              f"Generated {task_count} task files:\n"
                              f"• Task files: {len(created_tasks)} files\n"
                              f"• Index file: {index_filename}\n"
                              f"• Total images: {len(image_list)}\n"
                              f"• Saved to: {self.tasks_dir}")
            
            self.update_status(f"Generated {task_count} task files, total {len(image_list)} images")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate task files: {e}")
    
    def clear_all_tasks(self):
        """清理所有任务文件"""
        if not self.tasks_dir.exists():
            return
        
        try:
            # 删除所有JSON文件
            deleted_count = 0
            for file_path in self.tasks_dir.glob("*.json"):
                file_path.unlink()
                deleted_count += 1
            
            messagebox.showinfo("Success", f"Cleaned {deleted_count} task files")
            self.update_status(f"Cleaned {deleted_count} task files")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to clear task files: {e}")
    
    def update_status(self, message):
        """更新状态栏"""
        self.status_label.configure(text=message)

def main():
    """主函数"""
    root = tk.Tk()
    
    # 设置样式
    style = ttk.Style()
    style.theme_use('clam')
    
    # 创建应用
    app = TaskSplitter(root)
    
    # 启动应用
    root.mainloop()

if __name__ == "__main__":
    main()