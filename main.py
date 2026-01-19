import sys
from PyQt5.QtWidgets import QApplication, QMessageBox
from desktop_pet import DesktopPet

def main():
    # 确保应用程序单实例运行
    app = QApplication(sys.argv)
    
    # 检查必要的资源文件
    try:
        # 尝试导入并初始化桌宠
        pet = DesktopPet()
        pet.show()
        sys.exit(app.exec_())
    except FileNotFoundError as e:
        QMessageBox.critical(None, "资源缺失", f"启动失败：缺少必要的动画资源\n{str(e)}")
    except Exception as e:
        QMessageBox.critical(None, "启动错误", f"程序启动失败：\n{str(e)}")

if __name__ == "__main__":
    main()
