"""
集成测试脚本

测试完整的 OCR 处理流程
"""
import sys
import os
import requests
import base64
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Colors:
    """终端颜色"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'


def print_test(name):
    """打印测试名称"""
    print(f"\n{Colors.BLUE}{'=' * 60}{Colors.END}")
    print(f"{Colors.BLUE}{name}{Colors.END}")
    print(f"{Colors.BLUE}{'=' * 60}{Colors.END}")


def print_success(message):
    """打印成功消息"""
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")


def print_error(message):
    """打印错误消息"""
    print(f"{Colors.RED}✗ {message}{Colors.END}")


def print_info(message):
    """打印信息"""
    print(f"{Colors.YELLOW}  {message}{Colors.END}")


def test_module_imports():
    """测试模块导入"""
    print_test("测试 1: 模块导入")

    try:
        from config.settings import Config
        print_success("config.settings 导入成功")

        from services.pdf_processor import process_pdf
        print_success("services.pdf_processor 导入成功")

        from services.image_processor import preprocess_image
        print_success("services.image_processor 导入成功")

        from services.ocr_service import ocr_image
        print_success("services.ocr_service 导入成功")

        from services.task_manager import get_task_manager
        print_success("services.task_manager 导入成功")

        from utils.watermark_remover import remove_watermark
        print_success("utils.watermark_remover 导入成功")

        from utils.deskew_helper import deskew_image
        print_success("utils.deskew_helper 导入成功")

        return True
    except Exception as e:
        print_error(f"模块导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pdf_text_extraction():
    """测试 PDF 文本提取（需要测试PDF文件）"""
    print_test("测试 2: PDF 文本提取")

    try:
        from services.pdf_processor import process_pdf

        # 检查是否有测试文件
        test_files = [
            'test_text.pdf',
            'tests/fixtures/text.pdf',
        ]

        test_file = None
        for f in test_files:
            if Path(f).exists():
                test_file = f
                break

        if not test_file:
            print_info("跳过：未找到测试 PDF 文件")
            print_info("提示：创建 test_text.pdf 以测试此功能")
            return True

        result = process_pdf(test_file)
        print_success(f"PDF 处理成功")
        print_info(f"页数: {result.page_count}")
        print_info(f"策略: {result.strategy}")
        print_info(f"文本长度: {len(result.text)}")
        print_info(f"图片数: {len(result.images)}")

        return True
    except Exception as e:
        print_error(f"PDF 处理失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_image_preprocessing():
    """测试图片预处理"""
    print_test("测试 3: 图片预处理")

    try:
        import cv2
        import numpy as np
        from services.image_processor import preprocess_image
        from config.settings import Config

        # 创建测试图片
        Config.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        test_image_path = Config.TEMP_DIR / "test_preprocess.png"

        # 创建一个简单的测试图片（白底黑字）
        img = np.ones((200, 400, 3), dtype=np.uint8) * 255
        cv2.putText(img, "Test Image", (50, 100), cv2.FONT_HERSHEY_SIMPLEX,
                    2, (0, 0, 0), 3)

        # 添加一些浅色噪声（模拟水印）
        img[10:50, 10:100] = [255, 217, 217]  # #ffd9d9

        cv2.imwrite(str(test_image_path), img)
        print_info(f"创建测试图片: {test_image_path}")

        # 测试预处理
        output_path, stats = preprocess_image(
            str(test_image_path),
            remove_watermark=True,
            watermark_color=(255, 217, 217),
            deskew=True
        )

        print_success("图片预处理成功")
        print_info(f"水印已去除: {stats['watermark_removed']}")
        print_info(f"已纠偏: {stats['deskewed']}")
        if stats['deskewed']:
            print_info(f"倾斜角度: {stats['skew_angle']:.2f}°")

        # 清理
        test_image_path.unlink(missing_ok=True)
        Path(output_path).unlink(missing_ok=True)

        return True
    except Exception as e:
        print_error(f"图片预处理失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_task_manager():
    """测试任务管理器"""
    print_test("测试 4: 任务管理器")

    try:
        from services.task_manager import get_task_manager
        from api.error_handlers import RateLimitError

        task_manager = get_task_manager(max_concurrent=2)
        print_success("任务管理器创建成功")

        # 测试正常流程
        with task_manager.task_slot():
            print_success("获取任务槽位成功")
            status = task_manager.get_status()
            print_info(f"当前任务数: {status['current_tasks']}/{status['max_concurrent']}")

        # 测试限流
        try:
            with task_manager.task_slot():
                with task_manager.task_slot():
                    with task_manager.task_slot():  # 应该失败
                        pass
            print_error("限流测试失败：应该抛出异常")
            return False
        except RateLimitError:
            print_success("限流测试成功")

        return True
    except Exception as e:
        print_error(f"任务管理器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_endpoints(base_url="http://localhost:5000"):
    """测试 API 端点"""
    print_test("测试 5: API 端点")

    try:
        # 测试健康检查
        response = requests.get(f"{base_url}/api/v1/health", timeout=5)
        if response.status_code == 200:
            print_success("健康检查端点正常")
        else:
            print_error(f"健康检查失败: {response.status_code}")
            return False

        # 创建测试文件
        test_content = "This is a test file for OCR"
        test_file_path = Path("test_api.txt")
        test_file_path.write_text(test_content, encoding='utf-8')

        # 测试 OCR 端点
        with open(test_file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(
                f"{base_url}/api/v1/ocr",
                files=files,
                timeout=30
            )

        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print_success("OCR 端点正常")
                print_info(f"处理方法: {result['data']['metadata']['processing_method']}")
            else:
                print_error(f"OCR 请求失败: {result}")
                return False
        else:
            print_error(f"OCR 请求失败: {response.status_code}")
            return False

        # 清理
        test_file_path.unlink(missing_ok=True)

        return True
    except requests.exceptions.ConnectionError:
        print_info("跳过：服务未运行（需要先启动服务）")
        print_info("提示：运行 'python app.py' 启动服务")
        return True
    except Exception as e:
        print_error(f"API 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_error_handling():
    """测试错误处理"""
    print_test("测试 6: 错误处理")

    try:
        from api.validators import (
            parse_bool_param, parse_int_param,
            parse_color_param, ValidationError
        )
        from flask import Flask
        app = Flask(__name__)

        with app.test_request_context(
            '/test',
            data={'param1': 'invalid_number'}
        ):
            # 测试参数验证
            try:
                parse_int_param('param1')
                print_error("应该抛出 ValidationError")
                return False
            except ValidationError:
                print_success("参数验证错误处理正常")

        with app.test_request_context(
            '/test',
            data={'color': 'invalid_color'}
        ):
            # 测试颜色参数验证
            try:
                parse_color_param('color')
                print_error("应该抛出 ValidationError")
                return False
            except ValidationError:
                print_success("颜色参数验证正常")

        return True
    except Exception as e:
        print_error(f"错误处理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n")
    print(f"{Colors.BLUE}{'*' * 60}{Colors.END}")
    print(f"{Colors.BLUE}{'*' + ' ' * 58 + '*'}{Colors.END}")
    print(f"{Colors.BLUE}{'*' + ' ' * 18 + '集成测试套件' + ' ' * 18 + '*'}{Colors.END}")
    print(f"{Colors.BLUE}{'*' + ' ' * 58 + '*'}{Colors.END}")
    print(f"{Colors.BLUE}{'*' * 60}{Colors.END}")
    print("\n")

    results = []

    # 运行所有测试
    results.append(("模块导入", test_module_imports()))
    results.append(("PDF文本提取", test_pdf_text_extraction()))
    results.append(("图片预处理", test_image_preprocessing()))
    results.append(("任务管理器", test_task_manager()))
    results.append(("API端点", test_api_endpoints()))
    results.append(("错误处理", test_error_handling()))

    # 汇总结果
    print("\n")
    print(f"{Colors.BLUE}{'=' * 60}{Colors.END}")
    print(f"{Colors.BLUE}测试结果汇总{Colors.END}")
    print(f"{Colors.BLUE}{'=' * 60}{Colors.END}")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = f"{Colors.GREEN}✓ 通过{Colors.END}" if result else f"{Colors.RED}✗ 失败{Colors.END}"
        print(f"{name:20s} {status}")

    print(f"{Colors.BLUE}{'-' * 60}{Colors.END}")
    print(f"总计: {passed}/{total} 测试通过")
    print(f"{Colors.BLUE}{'=' * 60}{Colors.END}")

    if passed == total:
        print(f"\n{Colors.GREEN}🎉 所有集成测试通过！{Colors.END}\n")
        return 0
    else:
        print(f"\n{Colors.YELLOW}⚠️  部分测试失败，请检查错误信息{Colors.END}\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
