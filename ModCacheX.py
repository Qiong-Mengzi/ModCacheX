import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import shutil
import zipfile
import configparser
import toml
from typing import List, Dict, Any, Optional, Tuple
import logging
# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("modcachex.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ModCacheX")

class ModInfo:
    """模组信息类，存储模组的相关信息"""
    def __init__(self, file_path: str, name: str, size: int, version: Optional[str] = None):
        self.file_path: str = file_path  # 模组文件完整路径
        self.name: str = name            # 模组名称
        self.size: int = size            # 模组大小（字节）
        self.version: str | None = version      # 模组版本
        self.file_name: str = os.path.basename(file_path)  # 模组文件名

    def __str__(self) -> str:
        return f"ModInfo(name={self.name}, version={self.version}, size={self.size})"

class ModCacheX:
    """模组缓存管理器主类"""
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("ModCacheX - 模组缓存管理器")
        self.root.geometry("900x600")
        self.root.minsize(800, 500)
        
        # 配置
        self.config = configparser.ConfigParser()
        self.config_file = "modcachex.ini"
        self.cache_dir = ".modcache"
        self.max_cache_size = 0  # 0表示无限制，单位为MB
        
        # 模组列表
        self.mods: List[ModInfo] = []
        self.selected_mods: List[ModInfo] = []
        
        # 加载配置
        self.load_config()
        
        # 创建UI
        self.create_ui()
        
        # 初始化模组列表
        self.refresh_mod_list()
        
        # 绑定事件
        self.bind_events()
    
    def load_config(self) -> None:
        """加载配置文件"""
        if os.path.exists(self.config_file):
            try:
                self.config.read(self.config_file, encoding="utf-8")
                if "Settings" in self.config:
                    settings = self.config["Settings"]
                    self.cache_dir: str = settings.get("cache_dir", ".modcache")
                    self.max_cache_size = settings.getint("max_cache_size", 0)
                    logger.info(f"配置加载成功: 缓存目录={self.cache_dir}, 最大缓存={self.max_cache_size}MB")
            except Exception as e:
                logger.error(f"加载配置文件失败: {e}")
                messagebox.showerror("错误", f"加载配置文件失败: {e}")
        else:
            # 创建默认配置
            self.config["Settings"] = { # type: ignore
                "cache_dir": self.cache_dir,
                "max_cache_size": self.max_cache_size
            }
            self.save_config()
            logger.info("创建默认配置文件")
    
    def save_config(self) -> None:
        """保存配置文件"""
        try:
            if "Settings" not in self.config:
                self.config["Settings"] = {}
            self.config["Settings"]["cache_dir"] = self.cache_dir
            self.config["Settings"]["max_cache_size"] = str(self.max_cache_size)
            
            with open(self.config_file, "w", encoding="utf-8") as f:
                self.config.write(f)
            logger.info("配置保存成功")
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            messagebox.showerror("错误", f"保存配置文件失败: {e}")
    
    def create_ui(self) -> None:
        """创建用户界面"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 顶部控制区
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 缓存目录设置
        ttk.Label(control_frame, text="缓存目录:").pack(side=tk.LEFT, padx=(0, 5))
        self.cache_dir_var = tk.StringVar(value=self.cache_dir)
        cache_dir_entry = ttk.Entry(control_frame, textvariable=self.cache_dir_var, width=40)
        cache_dir_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        browse_btn = ttk.Button(control_frame, text="浏览...", command=self.browse_cache_dir)
        browse_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 最大缓存大小设置
        ttk.Label(control_frame, text="最大缓存(MB):").pack(side=tk.LEFT, padx=(0, 5))
        self.max_cache_var = tk.StringVar(value=str(self.max_cache_size) if self.max_cache_size > 0 else "")
        max_cache_entry = ttk.Entry(control_frame, textvariable=self.max_cache_var, width=10)
        max_cache_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        save_config_btn = ttk.Button(control_frame, text="保存配置", command=self.on_save_config)
        save_config_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        refresh_btn = ttk.Button(control_frame, text="刷新列表", command=self.refresh_mod_list)
        refresh_btn.pack(side=tk.LEFT)
        
        # 工具栏
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 10))
        
        import_btn = ttk.Button(toolbar, text="导入模组", command=self.import_mods)
        import_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        export_btn = ttk.Button(toolbar, text="导出模组", command=self.export_mods)
        export_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        export_zip_btn = ttk.Button(toolbar, text="导出为ZIP", command=self.export_mods_as_zip)
        export_zip_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        delete_btn = ttk.Button(toolbar, text="删除选中", command=self.delete_selected_mods)
        delete_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 搜索框
        search_frame = ttk.Frame(toolbar)
        search_frame.pack(side=tk.RIGHT)
        
        ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=20)
        search_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        search_btn = ttk.Button(search_frame, text="搜索", command=self.search_mods)
        search_btn.pack(side=tk.LEFT)
        
        # 模组列表
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建Treeview
        columns = ("name", "version", "size", "path")
        self.mod_tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        
        # 设置列标题和宽度
        self.mod_tree.heading("name", text="模组名称")
        self.mod_tree.heading("version", text="版本")
        self.mod_tree.heading("size", text="大小")
        self.mod_tree.heading("path", text="文件路径")
        
        self.mod_tree.column("name", width=200)
        self.mod_tree.column("version", width=100)
        self.mod_tree.column("size", width=80, anchor=tk.E)
        self.mod_tree.column("path", width=400)
        
        # 添加滚动条
        scrollbar_y = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.mod_tree.yview) # type: ignore
        scrollbar_x = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.mod_tree.xview) # type: ignore
        self.mod_tree.configure(yscroll=scrollbar_y.set, xscroll=scrollbar_x.set) # type: ignore
        
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.mod_tree.pack(fill=tk.BOTH, expand=True)
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
    
    def bind_events(self) -> None:
        """绑定事件处理"""
        # 绑定列表项选择事件
        self.mod_tree.bind("<<TreeviewSelect>>", self.on_mod_select)
        
        # 绑定列标题点击事件用于排序
        for col in ("name", "version", "size"):
            self.mod_tree.heading(col, text=self.mod_tree.heading(col)["text"], 
                                 command=lambda c=col: self.sort_tree(c))
    
    def browse_cache_dir(self) -> None:
        """浏览并选择缓存目录"""
        directory = filedialog.askdirectory(title="选择缓存目录", initialdir=self.cache_dir)
        if directory:
            self.cache_dir_var.set(directory)
    
    def on_save_config(self) -> None:
        """保存配置按钮事件处理"""
        try:
            # 更新配置
            self.cache_dir = self.cache_dir_var.get()
            max_cache_str = self.max_cache_var.get()
            self.max_cache_size = int(max_cache_str) if max_cache_str.strip() else 0
            
            # 保存配置
            self.save_config()
            
            # 刷新模组列表
            self.refresh_mod_list()
            
            self.status_var.set(f"配置已保存: 缓存目录={self.cache_dir}, 最大缓存={self.max_cache_size}MB")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的最大缓存大小(数字)")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            messagebox.showerror("错误", f"保存配置失败: {e}")
    
    def parse_mod_version(self, jar_path: str) -> Optional[str]:
        """解析JAR文件中的模组版本"""
        try:
            with zipfile.ZipFile(jar_path, 'r') as zip_ref:
                # 查找META-INF目录下的toml文件
                toml_files = [f for f in zip_ref.namelist() 
                             if f.startswith("META-INF/") and f.endswith(".toml")]
                
                if not toml_files:
                    return None
                
                # 读取第一个toml文件
                with zip_ref.open(toml_files[0]) as toml_file:
                    toml_content = toml_file.read().decode('utf-8')
                    data: Dict[str, Any] = toml.loads(toml_content)
                    
                    # 查找[[mods]]部分的version字段
                    if "mods" in data and isinstance(data["mods"], list) and len(data["mods"]) > 0: # type: ignore
                        mod_info: Dict[str, Any] = data["mods"][0] # type: ignore
                        if "version" in mod_info:
                            version: str = mod_info["version"] # type: ignore
                            # 检查是否包含美元符号
                            if "$" not in version:
                                return version # type: ignore
            return None
        except Exception as e:
            logger.warning(f"解析模组版本失败 {jar_path}: {e}")
            return None
    
    def get_cache_size(self) -> Tuple[int, str]:
        """获取缓存目录大小"""
        total_size = 0
        try:
            for dirpath, _, filenames in os.walk(self.cache_dir):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if os.path.isfile(fp):
                        total_size += os.path.getsize(fp)
        except Exception as e:
            logger.error(f"获取缓存大小失败: {e}")
        
        # 转换为人类可读的格式
        size_str = self.format_size(total_size)
        return total_size, size_str
    
    def format_size(self, size_bytes: int) -> str:
        """将字节大小转换为人类可读的格式"""
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        while size_bytes >= 1024 and unit_index < len(units) - 1:
            size_bytes //= 1024
            unit_index += 1
        return f"{size_bytes:.2f} {units[unit_index]}"
    
    def refresh_mod_list(self) -> None:
        """刷新模组列表"""
        self.status_var.set("正在加载模组列表...")
        self.root.update()
        
        # 清空当前列表
        for item in self.mod_tree.get_children():
            self.mod_tree.delete(item)
        self.mods = []
        
        # 检查缓存目录是否存在，不存在则创建
        if not os.path.exists(self.cache_dir):
            try:
                os.makedirs(self.cache_dir, exist_ok=True)
                logger.info(f"创建缓存目录: {self.cache_dir}")
            except Exception as e:
                logger.error(f"创建缓存目录失败: {e}")
                messagebox.showerror("错误", f"创建缓存目录失败: {e}")
                self.status_var.set("就绪")
                return
        
        # 遍历缓存目录查找JAR文件
        jar_files: list[str] = []
        for root, _, files in os.walk(self.cache_dir):
            for file in files:
                if file.lower().endswith('.jar'):
                    jar_files.append(os.path.join(root, file))
        
        # 获取缓存大小
        cache_size, cache_size_str = self.get_cache_size()
        
        # 解析JAR文件信息
        self.mods = []
        for jar_path in jar_files:
            try:
                file_name = os.path.basename(jar_path)
                size = os.path.getsize(jar_path)
                # 尝试解析模组名称和版本
                mod_name = file_name[:-4]  # 去掉.jar后缀
                version = self.parse_mod_version(jar_path)
                
                self.mods.append(ModInfo(jar_path, mod_name, size, version))
            except Exception as e:
                logger.error(f"处理模组文件失败 {jar_path}: {e}")
        
        # 显示模组列表
        for mod in self.mods:
            size_str = self.format_size(mod.size)
            self.mod_tree.insert("", tk.END, values=(mod.name, mod.version or "未知", size_str, mod.file_path))
        
        self.status_var.set(f"已加载 {len(self.mods)} 个模组，缓存大小: {cache_size_str}")
        
        # 检查缓存大小是否超过限制
        if self.max_cache_size > 0:
            cache_size_mb = cache_size / (1024 * 1024)
            if cache_size_mb > self.max_cache_size:
                self.status_var.set(f"警告: 缓存大小({cache_size_str})超过限制({self.max_cache_size}MB)")
    
    def on_mod_select(self, event: tk.Event) -> None:
        """模组选择事件处理"""
        selected_items = self.mod_tree.selection()
        self.selected_mods = []
        
        for item in selected_items:
            values = self.mod_tree.item(item, "values")
            if len(values) >= 4:
                # 查找对应的ModInfo对象
                mod_path = values[3]
                mod = next((m for m in self.mods if m.file_path == mod_path), None)
                if mod:
                    self.selected_mods.append(mod)
        
        self.status_var.set(f"已选择 {len(self.selected_mods)} 个模组")
    
    def sort_tree(self, col: str) -> None:
        """按列排序模组列表"""
        items = [(self.mod_tree.set(k, col), k) for k in self.mod_tree.get_children('')]
        
        # 数字类型排序
        if col == "size":
            def convert_size(size_str: str) -> float:
                size, unit = size_str.split()
                units = {'B': 1, 'KB': 1024, 'MB': 1024*1024, 'GB': 1024*1024*1024}
                return float(size) * units[unit]
            items.sort(key=lambda x: convert_size(x[0]))
        else:
            # 字符串类型排序
            items.sort(key=lambda x: x[0].lower())
        
        # 重新排列项目
        for index, (_, k) in enumerate(items):
            self.mod_tree.move(k, '', index)
    
    def import_mods(self) -> None:
        """导入模组"""
        files = filedialog.askopenfilenames(
            title="选择模组文件",
            filetypes=[("模组文件", "*.jar"), ("所有文件", "*.*")]
        )
        
        if not files:
            return
        
        self.status_var.set(f"正在导入 {len(files)} 个模组...")
        self.root.update()
        
        success_count = 0
        fail_count = 0
        failed_files: list[tuple[str, str]] = []
        
        for file_path in files:
            try:
                file_name = os.path.basename(file_path)
                dest_path = os.path.join(self.cache_dir, file_name)
                
                # 检查文件是否已存在
                if os.path.exists(dest_path):
                    # 询问是否覆盖
                    answer = messagebox.askyesnocancel(
                        "文件已存在", 
                        f"文件 '{file_name}' 已存在，是否覆盖？"
                    )
                    if answer is None:  # 取消操作
                        break
                    elif not answer:  # 不覆盖，跳过
                        continue
                
                # 复制文件
                shutil.copy2(file_path, dest_path)
                success_count += 1
                logger.info(f"成功导入模组: {file_name}")
            except Exception as e:
                fail_count += 1
                failed_files.append((file_path, str(e)))
                logger.error(f"导入模组失败 {file_path}: {e}")
        
        # 刷新模组列表
        self.refresh_mod_list()
        
        if success_count > 0:
            self.status_var.set(f"成功导入 {success_count} 个模组")
        if fail_count > 0:
            error_msg = "\n".join([f"{os.path.basename(f)}: {e}" for f, e in failed_files])
            messagebox.showerror("导入失败", f"以下 {fail_count} 个模组导入失败:\n{error_msg}")
    
    def export_mods(self) -> None:
        """导出模组"""
        if not self.selected_mods:
            messagebox.showinfo("提示", "请先选择要导出的模组")
            return
        
        directory = filedialog.askdirectory(title="选择导出目录")
        if not directory:
            return
        
        self.status_var.set(f"正在导出 {len(self.selected_mods)} 个模组...")
        self.root.update()
        
        success_count = 0
        fail_count = 0
        failed_files: list[tuple[str, str]] = []
        
        for mod in self.selected_mods:
            try:
                dest_path = os.path.join(directory, os.path.basename(mod.file_path))
                shutil.copy2(mod.file_path, dest_path)
                success_count += 1
                logger.info(f"成功导出模组: {mod.file_name}")
            except Exception as e:
                fail_count += 1
                failed_files.append((mod.file_name, str(e)))
                logger.error(f"导出模组失败 {mod.file_name}: {e}")
        
        if success_count > 0:
            self.status_var.set(f"成功导出 {success_count} 个模组")
        if fail_count > 0:
            error_msg = "\n".join([f"{f}: {e}" for f, e in failed_files])
            messagebox.showerror("导出失败", f"以下 {fail_count} 个模组导出失败:\n{error_msg}")
    
    def export_mods_as_zip(self) -> None:
        """将选中的模组导出为ZIP文件"""
        if not self.selected_mods:
            messagebox.showinfo("提示", "请先选择要导出的模组")
            return
        
        zip_file = filedialog.asksaveasfilename(
            title="保存ZIP文件",
            defaultextension=".zip",
            filetypes=[("ZIP文件", "*.zip"), ("所有文件", "*.*")]
        )
        
        if not zip_file:
            return
        
        self.status_var.set(f"正在打包 {len(self.selected_mods)} 个模组...")
        self.root.update()
        
        try:
            with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for mod in self.selected_mods:
                    arcname = os.path.basename(mod.file_path)
                    zipf.write(mod.file_path, arcname)
            
            self.status_var.set(f"成功打包 {len(self.selected_mods)} 个模组到 {os.path.basename(zip_file)}")
            logger.info(f"成功打包 {len(self.selected_mods)} 个模组到 {zip_file}")
        except Exception as e:
            messagebox.showerror("打包失败", f"打包模组失败: {e}")
            logger.error(f"打包模组失败: {e}")
    
    def delete_selected_mods(self) -> None:
        """删除选中的模组"""
        if not self.selected_mods:
            messagebox.showinfo("提示", "请先选择要删除的模组")
            return
        
        total_size = sum(mod.size for mod in self.selected_mods)
        size_str = self.format_size(total_size)
        
        answer = messagebox.askyesno(
            "确认删除", 
            f"确定要删除选中的 {len(self.selected_mods)} 个模组吗？\n"
            f"总大小: {size_str}\n"
            "此操作不可撤销！"
        )
        
        if not answer:
            return
        
        self.status_var.set(f"正在删除 {len(self.selected_mods)} 个模组...")
        self.root.update()
        
        success_count = 0
        fail_count = 0
        failed_files: list[tuple[str, str]] = []
        
        for mod in self.selected_mods:
            try:
                os.remove(mod.file_path)
                success_count += 1
                logger.info(f"成功删除模组: {mod.file_name}")
            except Exception as e:
                fail_count += 1
                failed_files.append((mod.file_name, str(e)))
                logger.error(f"删除模组失败 {mod.file_name}: {e}")
        
        # 刷新模组列表
        self.refresh_mod_list()
        
        if success_count > 0:
            self.status_var.set(f"成功删除 {success_count} 个模组")
        if fail_count > 0:
            error_msg = "\n".join([f"{f}: {e}" for f, e in failed_files])
            messagebox.showerror("删除失败", f"以下 {fail_count} 个模组删除失败:\n{error_msg}")
    
    def search_mods(self) -> None:
        """搜索模组"""
        search_text = self.search_var.get().lower().strip()
        if not search_text:
            # 如果搜索文本为空，则显示所有模组
            self.refresh_mod_list()
            return
        
        # 过滤模组
        filtered_mods = [
            mod for mod in self.mods 
            if search_text in mod.name.lower() 
            or (mod.version and search_text in mod.version.lower())
            or search_text in os.path.basename(mod.file_path).lower()
        ]
        
        # 清空当前列表
        for item in self.mod_tree.get_children():
            self.mod_tree.delete(item)
        
        # 显示过滤后的模组
        for mod in filtered_mods:
            size_str = self.format_size(mod.size)
            self.mod_tree.insert("", tk.END, values=(mod.name, mod.version or "未知", size_str, mod.file_path))
        
        self.status_var.set(f"找到 {len(filtered_mods)} 个匹配的模组")

def main() -> None:
    """主函数"""
    try:
        root = tk.Tk()
        try:
            root.wm_iconbitmap(default='icon.ico') # type: ignore
        except:
            ... # TODO: 其他可用的图标添加方法
        app = ModCacheX(root) # type: ignore
        root.mainloop()
    except Exception as e:
        logger.critical(f"程序崩溃: {e}", exc_info=True)
        messagebox.showerror("严重错误", f"程序崩溃: {e}\n请查看日志文件获取更多信息。")

if __name__ == "__main__":
    main()    