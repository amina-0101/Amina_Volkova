import unittest
import tkinter as tk
from unittest.mock import patch
import json
import os
import sys
import tempfile

# Добавляем корень проекта в sys.path для корректного импорта
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from book_tracker import BookTrackerApp


class TestBookTracker(unittest.TestCase):
    """Набор юнит-тестов для Book Tracker"""

    def setUp(self):
        # Создаём скрытое окно Tkinter для тестов
        self.root = tk.Tk()
        self.root.withdraw()  # Скрываем окно, чтобы не мешало
        self.app = BookTrackerApp(self.root)

        # Мокаем messagebox, чтобы тесты не блокировались диалогами
        self.msg_patcher = patch('book_tracker.messagebox')
        self.mock_msg = self.msg_patcher.start()

    def tearDown(self):
        self.msg_patcher.stop()
        self.root.destroy()
        # Удаляем временные файлы, если остались
        for f in [f for f in os.listdir('.') if f.startswith('test_books_')]:
            os.remove(f)

    # 🔧 Вспомогательный метод для программного заполнения полей
    def _fill_entries(self, title="", author="", genre="", pages=""):
        self.app.entries["Название книги:"].delete(0, tk.END)
        self.app.entries["Название книги:"].insert(0, title)
        self.app.entries["Автор:"].delete(0, tk.END)
        self.app.entries["Автор:"].insert(0, author)
        self.app.entries["Жанр:"].delete(0, tk.END)
        self.app.entries["Жанр:"].insert(0, genre)
        self.app.entries["Кол-во страниц:"].delete(0, tk.END)
        self.app.entries["Кол-во страниц:"].insert(0, pages)

    def _count_visible_rows(self):
        return len(self.app.tree.get_children())

    # ========================
    # ✅ ПОЗИТИВНЫЕ ТЕСТЫ
    # ========================
    def test_add_valid_book(self):
        self._fill_entries("1984", "Дж. Оруэлл", "Дистопия", "328")
        self.app.add_book()
        self.assertEqual(len(self.app.books), 1)
        self.assertEqual(self.app.books[0]["title"], "1984")
        self.assertTrue(self.mock_msg.showinfo.called)

    def test_add_multiple_books(self):
        for i in range(3):
            self._fill_entries(f"Книга{i}", "Автор", "Жанр", f"{100 + i}")
            self.app.add_book()
        self.assertEqual(len(self.app.books), 3)

    def test_save_and_load_json(self):
        self._fill_entries("Тестовая книга", "Тестовый автор", "Тест", "250")
        self.app.add_book()

        tmp_file = "test_books_io.json"
        self.app.data_file = tmp_file
        self.app.save_to_json()
        self.assertTrue(os.path.exists(tmp_file))

        # Имитируем загрузку в чистый список
        self.app.books.clear()
        self.app._refresh_table()
        self.app.load_from_json()

        self.assertEqual(len(self.app.books), 1)
        self.assertEqual(self.app.books[0]["pages"], 250)

    def test_filter_by_genre(self):
        self._fill_entries("B1", "A1", "Фантастика", "150")
        self.app.add_book()
        self._fill_entries("B2", "A2", "Детектив", "200")
        self.app.add_book()

        self.app.filter_genre.insert(0, "фанта")
        self.app.apply_filter()
        self.assertEqual(self._count_visible_rows(), 1)

    # ========================
    # ❌ НЕГАТИВНЫЕ ТЕСТЫ
    # ========================
    def test_add_empty_fields(self):
        self._fill_entries("", "Автор", "Жанр", "100")
        self.app.add_book()
        self.assertEqual(len(self.app.books), 0)
        self.assertTrue(self.mock_msg.showerror.called)

    def test_add_non_numeric_pages(self):
        self._fill_entries("Книга", "Автор", "Жанр", "abc")
        self.app.add_book()
        self.assertEqual(len(self.app.books), 0)

    def test_filter_invalid_pages(self):
        self._fill_entries("B1", "A1", "G1", "100")
        self.app.add_book()

        self.app.filter_pages.insert(0, "not_a_number")
        self.app.apply_filter()
        self.assertTrue(self.mock_msg.showerror.called)

    def test_load_missing_json_file(self):
        self.app.data_file = "definitely_not_exists.json"
        self.app.load_from_json()
        self.assertTrue(self.mock_msg.showwarning.called)

    # ========================
    # 📏 ГРАНИЧНЫЕ ТЕСТЫ
    # ========================
    def test_add_book_zero_pages(self):
        """0 страниц должно отклоняться валидацией"""
        self._fill_entries("Книга", "Автор", "Жанр", "0")
        self.app.add_book()
        self.assertEqual(len(self.app.books), 0)

    def test_add_book_negative_pages(self):
        """Отрицательные страницы должны отклоняться"""
        self._fill_entries("Книга", "Автор", "Жанр", "-50")
        self.app.add_book()
        self.assertEqual(len(self.app.books), 0)

    def test_filter_strict_greater_than_pages(self):
        """Фильтр > 200 не должен включать ровно 200 страниц"""
        self._fill_entries("B200", "A", "G", "200")
        self.app.add_book()
        self._fill_entries("B201", "A", "G", "201")
        self.app.add_book()

        self.app.filter_pages.insert(0, "200")
        self.app.apply_filter()
        self.assertEqual(self._count_visible_rows(), 1)  # Только B201

    def test_filter_case_insensitive_genre(self):
        """Поиск жанра не должен зависеть от регистра"""
        self._fill_entries("B1", "A1", "Научная Фантастика", "100")
        self.app.add_book()

        self.app.filter_genre.insert(0, "фантастика")
        self.app.apply_filter()
        self.assertEqual(self._count_visible_rows(), 1)

        self.app.reset_filter()
        self.app.filter_genre.insert(0, "НАУЧНАЯ")
        self.app.apply_filter()
        self.assertEqual(self._count_visible_rows(), 1)

    def test_filter_empty_result(self):
        """Фильтрация по несуществующему жанру должна вернуть 0 строк"""
        self._fill_entries("B1", "A1", "История", "100")
        self.app.add_book()

        self.app.filter_genre.insert(0, "Поэзия")
        self.app.apply_filter()
        self.assertEqual(self._count_visible_rows(), 0)

    def test_save_empty_list_warning(self):
        self.app.books.clear()
        self.app.data_file = "test_books_empty.json"
        self.app.save_to_json()
        self.assertTrue(self.mock_msg.showwarning.called)


if __name__ == "__main__":
    unittest.main()
