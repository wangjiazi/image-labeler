 #!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片标注工具
用于标注图片是highQuality还是lowQuality，并将图片移动到对应文件夹
"""

import os
import shutil
import json
import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import threading
from pathlib import Path
from collections import deque
from datetime import datetime

class ImageLabeler:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Labeling Tool - High Quality/Low Quality")
        self.root.geometry("1200x800")
        self.root.configure(bg='#f0f0f0')
        
        # 设置项目路径
        self.project_dir = Path(__file__).parent
        self.images_dir = self.project_dir / "images"  # 默认图片目录
        self.highQuality_dir = self.project_dir / "highQuality"
        self.lowQuality_dir = self.project_dir / "lowQuality"
        self.tasks_dir = self.project_dir / "tasks"
        self.progress_dir = self.project_dir / "progress"
        self.progress_file = self.progress_dir / "labeling_progress.json"
        
        # 注意：不再在启动时创建文件夹，只在导出时创建
        
        # 初始化变量
        self.current_image_path = None
        self.current_image_index = 0
        self.image_files = []
        self.labeled_files = {}  # 改为字典，保存文件名和标签的映射
        
        # 任务相关变量
        self.current_task = None
        self.task_files = []
        self.task_progress_file = None
        
        # 撤销功能
        self.undo_stack = deque(maxlen=10)  # 最多保存10次操作
        
        # 创建界面
        self.create_widgets()
        
        # 加载可用任务（在界面创建完成后）
        self.load_available_tasks()
        
        # 如果没有选择任务，显示提示
        if not self.task_files:
            self.show_no_task_message()
    
    def load_progress(self):
        """加载已标注的图片记录"""
        self.labeled_files = {}
        
        # 从进度文件读取已处理的文件信息
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'labeled_files' in data:
                        if isinstance(data['labeled_files'], dict):
                            # 从JSON文件中读取所有标注记录
                            self.labeled_files = data['labeled_files'].copy()
                            print(f"Loaded {len(self.labeled_files)} labeled records from progress file")
            except Exception as e:
                print(f"Failed to load progress file: {e}")
        else:
            print("Progress file does not exist, starting with empty labeled files")
    
    def save_progress(self):
        """保存标注进度"""
        try:
            data = {
                'labeled_files': self.labeled_files
            }
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存进度文件失败: {e}")
    
    def load_available_tasks(self):
        """加载可用的任务文件"""
        self.task_files = []
        if self.tasks_dir.exists():
            for file_path in self.tasks_dir.glob("*.json"):
                if file_path.name.startswith("task_"):
                    self.task_files.append(file_path)
        
        # 更新任务选择下拉框
        if hasattr(self, 'task_combobox'):
            task_names = [f.name for f in self.task_files]
            self.task_combobox['values'] = task_names
            if task_names:
                # 自动选择第一个任务并加载
                self.task_combobox.set(task_names[0])
                self.load_task(task_names[0])
                print(f"启动时自动加载任务: {task_names[0]}")
            else:
                print("没有找到可用的任务文件")
        else:
            print("任务选择下拉框尚未创建")
    
    def load_task(self, task_filename):
        """加载指定的任务"""
        if not task_filename:
            return
        
        task_path = self.tasks_dir / task_filename
        if not task_path.exists():
            messagebox.showerror("错误", f"任务文件不存在: {task_filename}")
            return
        
        try:
            with open(task_path, 'r', encoding='utf-8') as f:
                task_data = json.load(f)
            
            self.current_task = task_data
            self.current_task['filename'] = task_filename
            
            # 设置任务进度文件
            task_id = task_data.get('task_id', task_filename.replace('.json', ''))
            self.task_progress_file = self.progress_dir / f"task_progress_{task_id}.json"
            
            # 加载任务进度
            self.load_task_progress()
            
            # 获取任务中的图片
            self.get_task_images()
            
            # 显示第一张图片
            if self.image_files:
                self.current_image_index = 0
                self.show_current_image()
            else:
                self.show_completion_message()
            
            # 更新界面显示
            self.update_progress_display()
            self.update_stats_display()
            self.update_task_info()
            
            self.update_status(f"已加载任务: {task_data.get('task_name', task_filename)}")
            
        except Exception as e:
            messagebox.showerror("错误", f"加载任务失败: {e}")
    
    def load_task_progress(self):
        """加载任务进度"""
        self.labeled_files = {}
        
        if self.task_progress_file and self.task_progress_file.exists():
            try:
                with open(self.task_progress_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'labeled_files' in data:
                        self.labeled_files = data['labeled_files'].copy()
                        print(f"Loaded {len(self.labeled_files)} labeled records from task progress file")
                        
                        # 统计各类型标注数量
                        highQuality_count = sum(1 for label in self.labeled_files.values() if label == 'highQuality')
                        lowQuality_count = sum(1 for label in self.labeled_files.values() if label == 'lowQuality')
                        skip_count = sum(1 for label in self.labeled_files.values() if label == 'skip')
                        print(f"  Labeled statistics: highQuality={highQuality_count}, lowQuality={lowQuality_count}, skip={skip_count}")
            except Exception as e:
                print(f"Failed to load task progress file: {e}")
        else:
            print(f"Task progress file does not exist: {self.task_progress_file}")
    
    def save_task_progress(self):
        """保存任务进度"""
        if not self.task_progress_file:
            return
        
        try:
            data = {
                'task_id': self.current_task.get('task_id') if self.current_task else None,
                'labeled_files': self.labeled_files,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.task_progress_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to save task progress file: {e}")
    
    def get_task_images(self):
        """获取任务中的图片"""
        if not self.current_task:
            return
        
        # 获取任务中的图片文件名列表
        task_image_names = self.current_task.get('images', [])
        
        # 从images目录中找到对应的图片文件
        self.image_files = []
        for image_name in task_image_names:
            image_path = self.images_dir / image_name
            if image_path.exists():
                self.image_files.append(image_path)
            else:
                print(f"警告: 任务中的图片文件不存在: {image_name}")
        
        # 过滤掉已标注的图片（只显示未标注的图片）
        self.image_files = [img for img in self.image_files if img.name not in self.labeled_files]
        self.image_files.sort()  # 按文件名排序
    

    
    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # 标题
        title_label = ttk.Label(main_frame, text="Image Labeling Tool", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # 任务选择区域
        task_frame = ttk.LabelFrame(main_frame, text="Task selection", padding="10")
        task_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 任务选择行
        ttk.Label(task_frame, text="Select task:").grid(row=0, column=0, sticky=tk.W)
        self.task_combobox = ttk.Combobox(task_frame, width=40, state="readonly")
        self.task_combobox.grid(row=0, column=1, padx=(10, 10), sticky=(tk.W, tk.E))
        self.task_combobox.bind('<<ComboboxSelected>>', self.on_task_selected)
        
        refresh_button = ttk.Button(task_frame, text="Refresh task list", command=self.load_available_tasks)
        refresh_button.grid(row=0, column=2, padx=(0, 10))
        
        # 图片目录选择行
        ttk.Label(task_frame, text="Image directory:").grid(row=1, column=0, sticky=tk.W)
        self.images_dir_label = ttk.Label(task_frame, text=str(self.images_dir), 
                                         font=('Arial', 9), foreground='blue')
        self.images_dir_label.grid(row=1, column=1, padx=(10, 10), sticky=(tk.W, tk.E))
        
        select_images_button = ttk.Button(task_frame, text="Select image directory", 
                                        command=self.select_images_directory)
        select_images_button.grid(row=1, column=2, padx=(0, 10))
        
        # 任务信息
        self.task_info_label = ttk.Label(task_frame, text="", font=('Arial', 9))
        self.task_info_label.grid(row=2, column=0, columnspan=3, pady=(5, 0), sticky=tk.W)
        
        # 进度信息
        self.progress_label = ttk.Label(main_frame, text="", font=('Arial', 10))
        self.progress_label.grid(row=2, column=0, columnspan=3, pady=(0, 10))
        
        # 统计信息
        self.stats_label = ttk.Label(main_frame, text="", font=('Arial', 9))
        self.stats_label.grid(row=3, column=0, columnspan=3, pady=(0, 10))
        
        # 图片显示区域
        self.image_frame = ttk.Frame(main_frame, relief="solid", borderwidth=2)
        self.image_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        self.image_frame.columnconfigure(0, weight=1)
        self.image_frame.rowconfigure(0, weight=1)
        
        self.image_label = ttk.Label(self.image_frame, text="等待加载图片...")
        self.image_label.grid(row=0, column=0, padx=10, pady=10)
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=3, pady=20)
        
        # 标注按钮
        self.highQuality_button = ttk.Button(button_frame, text="🏺 High Quality (H)", 
                                     command=lambda: self.label_image("highQuality"))
        self.highQuality_button.grid(row=0, column=0, padx=10)
        
        self.lowQuality_button = ttk.Button(button_frame, text="🧩 Low Quality (L)", 
                                        command=lambda: self.label_image("lowQuality"))
        self.lowQuality_button.grid(row=0, column=1, padx=10)
        
        # 跳过按钮
        self.skip_button = ttk.Button(button_frame, text="⏭️ Skip (S)", 
                                    command=self.skip_image)
        self.skip_button.grid(row=0, column=2, padx=10)
        
        # 撤销按钮
        self.undo_button = ttk.Button(button_frame, text="↩️ Undo (Ctrl+Z)", 
                                    command=self.undo_last_label)
        self.undo_button.grid(row=0, column=3, padx=10)
        
        # 导出按钮
        self.export_button = ttk.Button(button_frame, text="📊 Export Results", 
                                      command=self.export_results)
        self.export_button.grid(row=0, column=4, padx=10)
        
        # 状态栏
        self.status_label = ttk.Label(main_frame, text="", font=('Arial', 9))
        self.status_label.grid(row=6, column=0, columnspan=3, pady=(10, 0))
        
        # 键盘快捷键
        self.root.bind('<Key>', self.handle_keypress)
        
        # 更新进度显示
        self.update_progress_display()
        self.update_stats_display()
    
    def on_task_selected(self, event):
        """任务选择事件处理"""
        selected_task = self.task_combobox.get()
        if selected_task:
            self.load_task(selected_task)
    
    def show_no_task_message(self):
        """显示无任务消息"""
        self.image_label.configure(text="📁 No available task files\n\nPlease put task files(.json) into tasks folder", 
                                 font=('Arial', 14))
        self.highQuality_button.configure(state='disabled')
        self.lowQuality_button.configure(state='disabled')
        self.skip_button.configure(state='disabled')
        self.update_status("等待任务文件")
    
    def select_images_directory(self):
        """选择图片目录"""
        directory = filedialog.askdirectory(
            title="Select image directory",
            initialdir=str(self.images_dir) if self.images_dir.exists() else str(self.project_dir)
        )
        
        if directory:
            self.images_dir = Path(directory)
            self.images_dir_label.configure(text=str(self.images_dir))
            self.update_status(f"Selected image directory: {self.images_dir}")
            
            # 如果当前有任务，重新加载任务图片
            if self.current_task:
                self.get_task_images()
                if self.image_files:
                    self.current_image_index = 0
                    self.show_current_image()
                else:
                    self.show_completion_message()
                self.update_progress_display()
                self.update_stats_display()
    
    def update_task_info(self):
        """更新任务信息显示"""
        if self.current_task:
            task_name = self.current_task.get('task_name', 'unknown task')
            total_images = self.current_task.get('total_images', 0)
            completed = len(self.labeled_files)
            remaining = total_images - completed
            
            info_text = f"Task Name:\t{task_name} \nTotal Images:\t{total_images} \nCompleted:\t\t{completed} \nRemaining:\t\t{remaining}"
            self.task_info_label.configure(text=info_text)
        else:
            self.task_info_label.configure(text="")
    
    def handle_keypress(self, event):
        """处理键盘快捷键"""
        if event.char.lower() == 'h':
            self.label_image("highQuality")
        elif event.char.lower() == 'l':
            self.label_image("lowQuality")
        elif event.char.lower() == 's':
            self.skip_image()
        # Ctrl+Z 现在通过专门的绑定处理，这里保留作为备用
        elif event.char.lower() == 'z' and (event.state & 0x4):  # Ctrl+Z
            self.undo_last_label()
    
    def show_current_image(self):
        """显示当前图片"""
        if not self.image_files or self.current_image_index >= len(self.image_files):
            self.show_completion_message()
            return
        
        self.current_image_path = self.image_files[self.current_image_index]
        
        try:
            # 加载并调整图片大小
            image = Image.open(self.current_image_path)
            
            # 计算合适的显示大小
            max_width = 800
            max_height = 600
            
            # 获取原始尺寸
            width, height = image.size
            
            # 计算缩放比例
            scale = min(max_width / width, max_height / height)
            
            if scale < 1:
                new_width = int(width * scale)
                new_height = int(height * scale)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 转换为PhotoImage
            photo = ImageTk.PhotoImage(image)
            
            # 更新图片显示
            self.image_label.configure(image=photo, text="")
            self.image_label.image = photo  # 保持引用
            
            # 更新状态
            self.update_status(f"Current Image: {self.current_image_path.name}")
            
        except Exception as e:
            self.image_label.configure(text=f"Failed to load image: {e}")
            self.update_status(f"Error: {e}")
    
    def show_completion_message(self):
        """显示完成消息"""
        if self.current_task:
            task_name = self.current_task.get('task_name', 'current task')
            self.image_label.configure(text=f"🎉 Task '{task_name}' is completed!\n\nAll images are labeled.", 
                                     font=('Arial', 14))
        else:
            self.image_label.configure(text="🎉 All images are labeled!\n\nYou can close the program or restart to check new images.", 
                                     font=('Arial', 14))
        
        self.highQuality_button.configure(state='disabled')
        self.lowQuality_button.configure(state='disabled')
        self.skip_button.configure(state='disabled')
        self.update_status("Labeling completed")
    
    def label_image(self, label_type):
        """标注图片"""
        if not self.current_image_path:
            return
        
        try:
            # 记录操作用于撤销
            undo_info = {
                'action': 'label',
                'original_path': str(self.current_image_path),
                'label_type': label_type,
                'filename': self.current_image_path.name
            }
            
            # 记录已标注（不移动文件）
            self.labeled_files[self.current_image_path.name] = label_type
            self.save_task_progress()
            
            # 添加到撤销栈
            self.undo_stack.append(undo_info)
            
            # 显示成功消息
            self.update_status(f"已标注为 {label_type}: {self.current_image_path.name}")
            
            # 移动到下一张图片
            self.next_image()
            
        except Exception as e:
            messagebox.showerror("错误", f"标注失败: {e}")
    
    def skip_image(self):
        """跳过当前图片"""
        if self.current_image_path:
            # 记录跳过
            self.labeled_files[self.current_image_path.name] = 'skip'
            self.save_task_progress()
            self.update_status(f"Skipped image: {self.current_image_path.name}")
            self.next_image()
    
    def undo_last_label(self):
        """撤销最后一次标注"""
        if not self.undo_stack:
            messagebox.showinfo("提示", "没有可撤销的操作")
            return
        
        try:
            # 获取最后一次操作
            last_action = self.undo_stack.pop()
            
            if last_action['action'] == 'label':
                # 从已标注列表中移除
                if last_action['filename'] in self.labeled_files:
                    del self.labeled_files[last_action['filename']]
                self.save_task_progress()
                
                # 重新获取图片列表
                self.get_task_images()
                self.current_image_index = 0
                self.update_progress_display()
                self.update_stats_display()
                
                if self.image_files:
                    self.show_current_image()
                
                self.update_status(f"Undone: {last_action['filename']}")
            
        except Exception as e:
            messagebox.showerror("错误", f"撤销操作失败: {e}")
    
    def next_image(self):
        """移动到下一张图片"""
        self.current_image_index += 1
        self.update_progress_display()
        self.update_stats_display()
        self.update_task_info()
        
        if self.current_image_index < len(self.image_files):
            self.show_current_image()
        else:
            self.show_completion_message()
    
    def update_progress_display(self):
        """更新进度显示"""
        if self.image_files:
            progress_text = f"Progress: {self.current_image_index + 1} / {len(self.image_files)}"
        else:
            progress_text = "No images to label"
        
        self.progress_label.configure(text=progress_text)
    
    def update_stats_display(self):
        """更新统计信息显示"""
        # 统计标注数据
        highQuality_labeled = sum(1 for label in self.labeled_files.values() if label == 'highQuality')
        lowQuality_labeled = sum(1 for label in self.labeled_files.values() if label == 'lowQuality')
        skip_count = sum(1 for label in self.labeled_files.values() if label == 'skip')
        total_labeled = len(self.labeled_files)
        
        stats_text = f"Stats: highQuality: {highQuality_labeled} | lowQuality: {lowQuality_labeled} | skip: {skip_count} | total: {total_labeled}"
        self.stats_label.configure(text=stats_text)
    
    def export_results(self):
        """导出标注结果"""
        if not self.current_task:
            messagebox.showwarning("Warning", "Please select a task first")
            return
        
        try:
            # 创建输出目录
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            task_id = self.current_task.get('task_id', 'unknown')
            output_dir = self.project_dir / "output" / f"task_{task_id}_{timestamp}"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 自动生成文件名
            csv_filename = f"task_{task_id}_results_{timestamp}.csv"
            csv_path = output_dir / csv_filename
            
            # 收集标注数据
            labeling_data = []
            
            # 从标注记录收集数据（从JSON文件中读取的标注信息）
            for filename, label in self.labeled_files.items():
                # 检查文件是否在images目录中
                image_file_path = self.images_dir / filename
                if image_file_path.exists():
                    labeling_data.append({
                        'filename': filename,
                        'label': label,
                        'folder': 'images',
                        'file_size': image_file_path.stat().st_size,
                        'modified_time': datetime.fromtimestamp(image_file_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    })
                else:
                    # 如果文件不存在，仍然记录标注信息，但标记为文件不存在
                    labeling_data.append({
                        'filename': filename,
                        'label': label,
                        'folder': 'not_found',
                        'file_size': 0,
                        'modified_time': 'N/A'
                    })
            
            # 写入CSV文件
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['filename', 'label', 'folder', 'file_size', 'modified_time']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for data in labeling_data:
                    writer.writerow(data)
            
            # 创建分类文件夹
            export_highQuality_dir = output_dir / "highQuality"
            export_lowQuality_dir = output_dir / "lowQuality"
            export_skip_dir = output_dir / "skip"
            export_unlabeled_dir = output_dir / "unlabeled"
            
            # 创建目录
            export_highQuality_dir.mkdir(parents=True, exist_ok=True)
            export_lowQuality_dir.mkdir(parents=True, exist_ok=True)
            export_skip_dir.mkdir(parents=True, exist_ok=True)
            export_unlabeled_dir.mkdir(parents=True, exist_ok=True)
            
            # 复制文件到对应目录
            moved_count = 0
            not_found_count = 0
            
            # 获取所有已标注的文件名集合
            labeled_filenames = set(self.labeled_files.keys())
            
            # 复制已标注的文件
            for filename, label in self.labeled_files.items():
                source_path = self.images_dir / filename
                if source_path.exists():
                    if label == 'highQuality':
                        target_path = export_highQuality_dir / filename
                    elif label == 'lowQuality':
                        target_path = export_lowQuality_dir / filename
                    elif label == 'skip':
                        target_path = export_skip_dir / filename
                    else:
                        continue
                    
                    try:
                        shutil.copy2(str(source_path), str(target_path))
                        moved_count += 1
                    except Exception as e:
                        print(f"复制文件失败 {filename}: {e}")
                else:
                    not_found_count += 1
                    print(f"文件不存在: {filename}")
            
            # 复制未标注的文件（只针对当前task中的图片）
            unlabeled_count = 0
            task_image_names = set(self.current_task.get('images', []))
            for file_path in self.images_dir.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in {'.jpg', '.jpeg', '.jpe', '.png', '.bmp', '.gif', '.tiff'}:
                    # 只处理当前task中的图片
                    if file_path.name in task_image_names and file_path.name not in labeled_filenames:
                        target_path = export_unlabeled_dir / file_path.name
                        try:
                            shutil.copy2(str(file_path), str(target_path))
                            unlabeled_count += 1
                        except Exception as e:
                            print(f"复制未标注文件失败 {file_path.name}: {e}")
            
            # 生成统计报告
            report_path = output_dir / f"task_{task_id}_report_{timestamp}.txt"
            self.generate_report(report_path, labeling_data)
            
            # 复制任务进度文件
            if self.task_progress_file and self.task_progress_file.exists():
                progress_copy_path = output_dir / f"task_progress_{task_id}_{timestamp}.json"
                shutil.copy2(str(self.task_progress_file), str(progress_copy_path))
            
            messagebox.showinfo("Export success", 
                              f"Task results have been exported to:\n{output_dir}\n\n"
                              f"Contains:\n"
                              f"• CSV result file: {csv_filename}\n"
                              f"• Statistics report: task_{task_id}_report_{timestamp}.txt\n"
                              f"• Task progress file: task_progress_{task_id}_{timestamp}.json\n"
                              f"• Classified image folders: highQuality, lowQuality, skip, unlabeled\n\n"
                              f"Processed {moved_count} labeled files, {unlabeled_count} unlabeled files, {not_found_count} files not found")
            
            self.update_status(f"Task {task_id} results have been exported with {len(labeling_data)} labeled records")
            
        except Exception as e:
            messagebox.showerror("Export failed", f"Error during export: {e}")
    
    def generate_report(self, report_path, labeling_data):
        """生成统计报告"""
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("Task labeling results statistics report\n")
                f.write("=" * 50 + "\n")
                f.write(f"Task ID: {self.current_task.get('task_id', 'unknown')}\n")
                f.write(f"Task name: {self.current_task.get('task_name', 'unknown')}\n")
                f.write(f"Generated time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # 总体统计
                total_count = len(labeling_data)
                highQuality_count = len([d for d in labeling_data if d['label'] == 'highQuality'])
                lowQuality_count = len([d for d in labeling_data if d['label'] == 'lowQuality'])
                skip_count = len([d for d in labeling_data if d['label'] == 'skip'])
                
                # 统计未标注文件（只针对当前task中的图片）
                unlabeled_count = 0
                task_image_names = set(self.current_task.get('images', []))
                for file_path in self.images_dir.iterdir():
                    if file_path.is_file() and file_path.suffix.lower() in {'.jpg', '.jpeg', '.jpe', '.png', '.bmp', '.gif', '.tiff'}:
                        # 只统计当前task中的未标注图片
                        if file_path.name in task_image_names and file_path.name not in self.labeled_files:
                            unlabeled_count += 1
                
                total_all_files = total_count + unlabeled_count
                
                f.write("Overall statistics:\n")
                f.write(f"  Total labeled: {total_count}\n")
                f.write(f"  highQuality: {highQuality_count}\n")
                f.write(f"  lowQuality: {lowQuality_count}\n")
                f.write(f"  skip: {skip_count}\n")
                f.write(f"  unlabeled: {unlabeled_count}\n")
                f.write(f"  total files: {total_all_files}\n")
                f.write(f"  highQuality ratio: {highQuality_count/total_count*100:.1f}%\n" if total_count > 0 else "  highQuality ratio: 0%\n")
                f.write(f"  lowQuality ratio: {lowQuality_count/total_count*100:.1f}%\n" if total_count > 0 else "  lowQuality ratio: 0%\n")
                f.write(f"  skip ratio: {skip_count/total_count*100:.1f}%\n" if total_count > 0 else "  skip ratio: 0%\n")
                f.write(f"  unlabeled ratio: {unlabeled_count/total_all_files*100:.1f}%\n" if total_all_files > 0 else "  unlabeled ratio: 0%\n\n")
                
                # 文件大小统计
                total_size = sum(d['file_size'] for d in labeling_data)
                avg_size = total_size / total_count if total_count > 0 else 0
                
                f.write("File size statistics:\n")
                f.write(f"  Total size: {total_size / 1024 / 1024:.2f} MB\n")
                f.write(f"  Average size: {avg_size / 1024:.2f} KB\n\n")
                
                # 按标签分类的文件列表
                f.write("highQuality file list:\n")
                f.write("-" * 30 + "\n")
                highQuality_files = [d for d in labeling_data if d['label'] == 'highQuality']
                for data in sorted(highQuality_files, key=lambda x: x['filename']):
                    f.write(f"  {data['filename']} ({data['file_size']/1024:.1f} KB)\n")
                
                f.write("\nlowQuality file list:\n")
                f.write("-" * 30 + "\n")
                lowQuality_files = [d for d in labeling_data if d['label'] == 'lowQuality']
                for data in sorted(lowQuality_files, key=lambda x: x['filename']):
                    f.write(f"  {data['filename']} ({data['file_size']/1024:.1f} KB)\n")
                
                f.write("\nskip file list:\n")
                f.write("-" * 30 + "\n")
                skip_files = [d for d in labeling_data if d['label'] == 'skip']
                for data in sorted(skip_files, key=lambda x: x['filename']):
                    f.write(f"  {data['filename']} ({data['file_size']/1024:.1f} KB)\n")
                
                # 未标注文件统计（只针对当前task中的图片）
                unlabeled_files = []
                task_image_names = set(self.current_task.get('images', []))
                for file_path in self.images_dir.iterdir():
                    if file_path.is_file() and file_path.suffix.lower() in {'.jpg', '.jpeg', '.jpe', '.png', '.bmp', '.gif', '.tiff'}:
                        # 只统计当前task中的未标注图片
                        if file_path.name in task_image_names and file_path.name not in self.labeled_files:
                            unlabeled_files.append({
                                'filename': file_path.name,
                                'file_size': file_path.stat().st_size,
                                'modified_time': datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                            })
                
                f.write(f"\nUnlabeled file list (total {len(unlabeled_files)} files):\n")
                f.write("-" * 30 + "\n")
                for data in sorted(unlabeled_files, key=lambda x: x['filename']):
                    f.write(f"  {data['filename']} ({data['file_size']/1024:.1f} KB)\n")
                
        except Exception as e:
            print(f"Failed to generate report: {e}")
    
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
    app = ImageLabeler(root)
    
    # 启动应用
    root.mainloop()

if __name__ == "__main__":
    main()