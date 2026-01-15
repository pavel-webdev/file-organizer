#!/usr/bin/env python3

import os
import shutil
import re
from datetime import datetime
from pathlib import Path
import logging
import json
from typing import Dict, List, Tuple, Optional

class FileOrganizer:
    """Основной класс для организации файлов"""
    
    # Словарь категорий файлов
    FILE_CATEGORIES = {
        'lecture': ['лекция', 'lecture', 'теория', 'theory', 'доклад'],
        'practice': ['практика', 'practice', 'задание', 'task', 'упражнение'],
        'project': ['проект', 'project', 'курсовая', 'диплом', 'исследование'],
        'lab': ['лаба', 'lab', 'лабораторная', 'experiment'],
        'material': ['материал', 'material', 'ресурс', 'resource', 'дополнительно'],
        'exam': ['экзамен', 'exam', 'зачет', 'test', 'контрольная']
    }
    
    # Расширения файлов по типам
    FILE_TYPES = {
        'documents': ['.pdf', '.doc', '.docx', '.txt', '.rtf'],
        'presentations': ['.ppt', '.pptx', '.key'],
        'spreadsheets': ['.xls', '.xlsx', '.csv'],
        'code': ['.py', '.java', '.cpp', '.js', '.html', '.css', '.sql'],
        'archives': ['.zip', '.rar', '.7z', '.tar', '.gz'],
        'images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg'],
        'other': []  # Все остальное
    }
    
    def __init__(self, source_dir: str, target_dir: Optional[str] = None):
        """
        Инициализация органайзера
        
        Args:
            source_dir: Исходная папка с файлами
            target_dir: Целевая папка (если None, то source_dir + '_organized')
        """
        self.source_dir = Path(source_dir).resolve()
        if target_dir:
            self.target_dir = Path(target_dir).resolve()
        else:
            self.target_dir = self.source_dir.parent / f"{self.source_dir.name}_organized"
        
        # Создаем целевую папку если не существует
        self.target_dir.mkdir(exist_ok=True)
        
        # Настройка логирования
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.target_dir / 'organizer.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        self.stats = {
            'total_files': 0,
            'processed': 0,
            'skipped': 0,
            'errors': 0,
            'categories': {},
            'start_time': datetime.now()
        }
    
    def analyze_filename(self, filename: str) -> Dict:
        """
        Анализирует имя файла и извлекает информацию
        
        Returns:
            Словарь с информацией о файле
        """
        info = {
            'original_name': filename,
            'subject': None,
            'category': 'other',
            'date': None,
            'file_type': 'other',
            'new_name': None
        }
        
        # Приводим к нижнему регистру для анализа
        name_lower = filename.lower()
        
        # Определяем предмет (по паттернам)
        subject_patterns = {
            'math': ['матема', 'math', 'алгебр', 'геометр'],
            'programming': ['програм', 'program', 'код', 'алгоритм'],
            'database': ['баз', 'database', 'sql', 'бд'],
            'web': ['веб', 'web', 'html', 'css', 'js'],
            'english': ['англ', 'english', 'инглиш'],
            'physics': ['физик', 'physics']
        }
        
        for subject, patterns in subject_patterns.items():
            if any(pattern in name_lower for pattern in patterns):
                info['subject'] = subject
                break
        
        # Определяем категорию
        for category, keywords in self.FILE_CATEGORIES.items():
            if any(keyword in name_lower for keyword in keywords):
                info['category'] = category
                break
        
        # Ищем дату в форматах: DD-MM-YYYY, YYYY-MM-DD, DD.MM.YYYY
        date_patterns = [
            r'(\d{2})[-.](\d{2})[-.](\d{4})',
            r'(\d{4})[-.](\d{2})[-.](\d{2})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, filename)
            if match:
                try:
                    if len(match.group(1)) == 4:  # YYYY-MM-DD
                        year, month, day = match.groups()
                    else:  # DD-MM-YYYY
                        day, month, year = match.groups()
                    
                    info['date'] = f"{year}-{month}-{day}"
                    break
                except:
                    continue
        
        # Определяем тип файла по расширению
        ext = Path(filename).suffix.lower()
        for file_type, extensions in self.FILE_TYPES.items():
            if ext in extensions:
                info['file_type'] = file_type
                break
        
        return info
    
    def generate_new_name(self, file_info: Dict, counter: int = 1) -> str:
        """
        Генерирует новое имя файла по шаблону
        
        Формат: [Предмет]_[Категория]_[Дата]_[Тип]_[Номер].[расширение]
        Пример: math_lecture_2024-03-15_presentation_01.pptx
        """
        name_parts = []
        
        # Предмет (если определен)
        if file_info['subject']:
            name_parts.append(file_info['subject'])
        else:
            name_parts.append('unknown')
        
        # Категория
        name_parts.append(file_info['category'])
        
        # Дата (если есть, иначе текущая)
        if file_info['date']:
            name_parts.append(file_info['date'])
        else:
            name_parts.append(datetime.now().strftime('%Y-%m-%d'))
        
        # Тип файла
        name_parts.append(file_info['file_type'])
        
        # Номер для уникальности
        name_parts.append(f"{counter:02d}")
        
        # Расширение
        ext = Path(file_info['original_name']).suffix
        
        # Собираем имя
        new_name = '_'.join(name_parts) + ext
        return new_name
    
    def organize_file(self, file_path: Path) -> bool:
        """
        Обрабатывает один файл
        """
        try:
            # Анализируем имя файла
            file_info = self.analyze_filename(file_path.name)
            self.stats['total_files'] += 1
            
            # Пропускаем системные файлы
            if file_path.name.startswith('.') or file_path.name in ['desktop.ini', 'thumbs.db']:
                self.logger.debug(f"Пропущен системный файл: {file_path.name}")
                self.stats['skipped'] += 1
                return False
            
            # Генерируем новое имя (с проверкой на уникальность)
            target_subdir = file_info['category']
            target_path = self.target_dir / target_subdir
            
            # Создаем подпапку если нужно
            target_path.mkdir(exist_ok=True)
            
            # Генерируем уникальное имя
            counter = 1
            while True:
                new_name = self.generate_new_name(file_info, counter)
                new_path = target_path / new_name
                if not new_path.exists():
                    break
                counter += 1
            
            file_info['new_name'] = new_name
            
            # Копируем файл (можно заменить на shutil.move для перемещения)
            shutil.copy2(file_path, new_path)
            
            # Обновляем статистику
            self.stats['processed'] += 1
            if target_subdir not in self.stats['categories']:
                self.stats['categories'][target_subdir] = 0
            self.stats['categories'][target_subdir] += 1
            
            self.logger.info(f"Обработан: {file_path.name} -> {new_name}")
            
            # Сохраняем информацию о файле (опционально)
            self.save_file_info(file_info, new_path)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка обработки {file_path.name}: {str(e)}")
            self.stats['errors'] += 1
            return False
    
    def save_file_info(self, file_info: Dict, file_path: Path):
        """
        Сохраняет метаданные файла в JSON (опционально)
        """
        meta_dir = self.target_dir / '_metadata'
        meta_dir.mkdir(exist_ok=True)
        
        meta_file = meta_dir / f"{file_path.stem}.json"
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(file_info, f, ensure_ascii=False, indent=2)
    
    def generate_report(self):
        """
        Генерирует отчет о проделанной работе
        """
        end_time = datetime.now()
        duration = end_time - self.stats['start_time']
        
        report = {
            'summary': {
                'source_directory': str(self.source_dir),
                'target_directory': str(self.target_dir),
                'start_time': self.stats['start_time'].isoformat(),
                'end_time': end_time.isoformat(),
                'duration_seconds': duration.total_seconds(),
                'total_files_found': self.stats['total_files'],
                'successfully_processed': self.stats['processed'],
                'skipped_files': self.stats['skipped'],
                'errors': self.stats['errors']
            },
            'categories': self.stats['categories'],
            'timestamp': datetime.now().isoformat()
        }
        
        # Сохраняем отчет
        report_file = self.target_dir / 'organization_report.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # Выводим краткий отчет в консоль
        print("\n" + "="*50)
        print("ОТЧЕТ ОБ ОРГАНИЗАЦИИ ФАЙЛОВ")
        print("="*50)
        print(f"Исходная папка: {self.source_dir}")
        print(f"Целевая папка: {self.target_dir}")
        print(f"Найдено файлов: {self.stats['total_files']}")
        print(f"Успешно обработано: {self.stats['processed']}")
        print(f"Пропущено: {self.stats['skipped']}")
        print(f"Ошибок: {self.stats['errors']}")
        print(f"Затрачено времени: {duration.total_seconds():.2f} секунд")
        
        if self.stats['categories']:
            print("\nРаспределение по категориям:")
            for category, count in self.stats['categories'].items():
                print(f"  {category}: {count} файлов")
        
        print(f"\nПодробный отчет сохранен: {report_file}")
        print("="*50)
        
        return report
    
    def run(self, recursive: bool = False):
        """
        Запускает процесс организации файлов
        
        Args:
            recursive: Рекурсивно обходить подпапки
        """
        self.logger.info(f"Запуск организации файлов из: {self.source_dir}")
        
        # Получаем список файлов
        if recursive:
            files = list(self.source_dir.rglob('*'))
        else:
            files = list(self.source_dir.glob('*'))
        
        # Фильтруем только файлы (не папки)
        files = [f for f in files if f.is_file()]
        
        self.logger.info(f"Найдено {len(files)} файлов для обработки")
        
        # Обрабатываем каждый файл
        for file_path in files:
            self.organize_file(file_path)
        
        # Генерируем отчет
        self.generate_report()


def main():
    """
    Точка входа в программу
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description='File Organizer Pro - автоматическая сортировка учебных материалов'
    )
    parser.add_argument(
        'source',
        help='Исходная папка с файлами для организации'
    )
    parser.add_argument(
        '-t', '--target',
        help='Целевая папка (по умолчанию: source_organized)'
    )
    parser.add_argument(
        '-r', '--recursive',
        action='store_true',
        help='Рекурсивная обработка подпапок'
    )
    parser.add_argument(
        '-d', '--dry-run',
        action='store_true',
        help='Тестовый режим (без реального копирования)'
    )
    
    args = parser.parse_args()
    
    # Проверяем существование исходной папки
    source_path = Path(args.source)
    if not source_path.exists():
        print(f"Ошибка: Папка '{args.source}' не существует!")
        return 1
    
    # Запускаем органайзер
    organizer = FileOrganizer(args.source, args.target)
    
    # В режиме dry-run меняем логику
    if args.dry_run:
        organizer.logger.info("РЕЖИМ ТЕСТИРОВАНИЯ (dry-run)")
        # Здесь можно добавить логику имитации
        # Например, только анализ без копирования
    
    organizer.run(recursive=args.recursive)
    
    return 0


if __name__ == '__main__':
    exit(main())