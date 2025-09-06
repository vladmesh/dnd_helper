#!/usr/bin/env python3
import subprocess
import os
import json
from datetime import datetime

class GitOperations:
    def __init__(self, repo_path="/home/ubuntu/dnd_helper"):
        self.repo_path = repo_path
        self.branch_name = f"update-monster-translations-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    def run_command(self, command, cwd=None):
        """Выполняет команду и возвращает результат"""
        if cwd is None:
            cwd = self.repo_path
        
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                cwd=cwd, 
                capture_output=True, 
                text=True,
                check=True
            )
            return True, result.stdout.strip()
        except subprocess.CalledProcessError as e:
            return False, e.stderr.strip()
    
    def check_git_status(self):
        """Проверяет статус git репозитория"""
        print("Проверяю статус git репозитория...")
        
        success, output = self.run_command("git status --porcelain")
        if not success:
            print(f"❌ Ошибка проверки статуса: {output}")
            return False
        
        if output:
            print("📝 Найдены изменения в репозитории:")
            print(output)
        else:
            print("✅ Рабочая директория чистая")
        
        return True
    
    def create_branch(self):
        """Создает новую ветку"""
        print(f"Создаю новую ветку: {self.branch_name}")
        
        # Переключаемся на main и подтягиваем изменения
        success, output = self.run_command("git checkout main")
        if not success:
            print(f"❌ Не удалось переключиться на main: {output}")
            return False
        
        success, output = self.run_command("git pull origin main")
        if not success:
            print(f"⚠️ Предупреждение при pull: {output}")
        
        # Создаем новую ветку
        success, output = self.run_command(f"git checkout -b {self.branch_name}")
        if not success:
            print(f"❌ Не удалось создать ветку: {output}")
            return False
        
        print(f"✅ Ветка {self.branch_name} создана")
        return True
    
    def replace_monsters_file(self, updated_file_path):
        """Заменяет файл с монстрами на обновленный"""
        original_file = os.path.join(self.repo_path, "seed_data_monsters.json")
        
        print(f"Заменяю {original_file} на {updated_file_path}")
        
        # Копируем обновленный файл
        success, output = self.run_command(f"cp {updated_file_path} {original_file}")
        if not success:
            print(f"❌ Не удалось скопировать файл: {output}")
            return False
        
        print("✅ Файл заменен")
        return True
    
    def commit_changes(self, stats_message=""):
        """Коммитит изменения"""
        print("Коммичу изменения...")
        
        # Добавляем файл в индекс
        success, output = self.run_command("git add seed_data_monsters.json")
        if not success:
            print(f"❌ Не удалось добавить файл в индекс: {output}")
            return False
        
        # Создаем коммит
        commit_message = f"Обновление русских переводов монстров\n\n{stats_message}"
        
        success, output = self.run_command(f'git commit -m "{commit_message}"')
        if not success:
            print(f"❌ Не удалось создать коммит: {output}")
            return False
        
        print("✅ Изменения закоммичены")
        return True
    
    def push_branch(self):
        """Пушит ветку в репозиторий"""
        print(f"Пушу ветку {self.branch_name} в репозиторий...")
        
        success, output = self.run_command(f"git push origin {self.branch_name}")
        if not success:
            print(f"❌ Не удалось запушить ветку: {output}")
            return False
        
        print("✅ Ветка запушена")
        return True
    
    def create_pull_request(self):
        """Создает pull request через GitHub CLI"""
        print("Создаю pull request...")
        
        pr_title = "Обновление русских переводов монстров"
        pr_body = """Автоматическое обновление русских названий и описаний монстров.

## Изменения
- Добавлены недостающие русские названия монстров
- Добавлены недостающие русские описания монстров
- Исправлены случаи, где вместо русских названий были английские

## Источник данных
Данные получены путем парсинга сайта dnd.su/bestiary/

## Проверка
- [x] Автоматическая проверка соответствия названий
- [x] Валидация JSON структуры
- [x] Проверка качества переводов

Готово к ревью и мержу."""
        
        success, output = self.run_command(
            f'gh pr create --title "{pr_title}" --body "{pr_body}" --base main --head {self.branch_name}'
        )
        
        if not success:
            print(f"❌ Не удалось создать pull request: {output}")
            return False, None
        
        # Извлекаем URL pull request из вывода
        pr_url = None
        for line in output.split('\n'):
            if 'https://github.com' in line:
                pr_url = line.strip()
                break
        
        print(f"✅ Pull request создан: {pr_url}")
        return True, pr_url
    
    def run_full_workflow(self, updated_file_path, stats_message=""):
        """Выполняет полный workflow: ветка -> коммит -> push -> PR"""
        print("🚀 Запуск полного git workflow")
        print("=" * 50)
        
        # Проверяем статус
        if not self.check_git_status():
            return False, None
        
        # Создаем ветку
        if not self.create_branch():
            return False, None
        
        # Заменяем файл
        if not self.replace_monsters_file(updated_file_path):
            return False, None
        
        # Коммитим
        if not self.commit_changes(stats_message):
            return False, None
        
        # Пушим
        if not self.push_branch():
            return False, None
        
        # Создаем PR
        success, pr_url = self.create_pull_request()
        if not success:
            return False, None
        
        print(f"\n🎉 Workflow завершен успешно!")
        print(f"🌿 Ветка: {self.branch_name}")
        print(f"🔗 Pull Request: {pr_url}")
        
        return True, pr_url

def main():
    # Пример использования
    git_ops = GitOperations()
    
    updated_file = "/home/ubuntu/seed_data_monsters_updated.json"
    stats = "Обновлено X монстров с недостающими переводами"
    
    success, pr_url = git_ops.run_full_workflow(updated_file, stats)
    
    if success:
        print(f"\n✅ Git операции завершены успешно!")
        print(f"Pull Request: {pr_url}")
    else:
        print(f"\n❌ Ошибка в git операциях")

if __name__ == "__main__":
    main()

