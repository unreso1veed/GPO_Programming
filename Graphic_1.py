import subprocess
import os
import pandas as pd
import numpy as np
from pathlib import Path

def get_filename_from_user():
    """Получает название файла от пользователя"""
    print("📁 Файлы в текущей директории:")
    script_dir = Path(__file__).parent.absolute()
    
    # Показываем только файлы данных
    data_files = []
    for ext in ['.txt', '.csv', '.dat']:
        data_files.extend(script_dir.glob(f"*{ext}"))
    
    if data_files:
        print("Доступные файлы данных:")
        for file in data_files:
            print(f"  📄 {file.name}")
    else:
        print("  ❌ Файлов данных не найдено")
    
    print("\n" + "="*50)
    filename = input("Введите название файла с данными (например: zapis_04_09.txt): ").strip()
    
    # Проверяем существование файла
    data_file = script_dir / filename
    if not data_file.exists():
        print(f"❌ Файл '{filename}' не найден!")
        print("Проверьте правильность названия и попробуйте снова.")
        return None
    
    return filename

def process_and_create_plot(filename):
    """
    Обрабатывает данные и создает сглаженный график
    Смещение повторяющихся точек на 0.05 секунды
    """
    script_dir = Path(__file__).parent.absolute()
    data_file = script_dir / filename
    base_name = Path(filename).stem  # Имя файла без расширения
    
    # Создаем имена файлов на основе входного файла
    output_file = script_dir / f"{base_name}_processed.png"
    processed_data_file = script_dir / f"{base_name}_processed.txt"
    smoothed_data_file = script_dir / f"{base_name}_smoothed.txt"
    
    print(f"📊 Обрабатываем файл: {filename}")
    print(f"📁 Будет создано:")
    print(f"  📊 {output_file.name}")
    print(f"  📝 {processed_data_file.name}")
    
    # Читаем данные
    try:
        # Пробуем разные разделители
        try:
            df = pd.read_csv(data_file, header=None, names=['Time', 'SensorValue'], sep=',')
        except:
            try:
                df = pd.read_csv(data_file, header=None, names=['Time', 'SensorValue'], sep=';')
            except:
                df = pd.read_csv(data_file, header=None, names=['Time', 'SensorValue'], sep='\s+')
        
        print(f"✅ Исходные данные: {len(df)} записей")
        print(f"📈 Уникальных значений времени: {df['Time'].nunique()}")
        
        # Анализируем проблему
        time_diff = np.diff(df['Time'])
        repeated_times = sum(time_diff == 0)
        print(f"🔍 Повторяющихся временных точек: {repeated_times}")
        
        if repeated_times > 0:
            print("⚠️  Обнаружены повторяющиеся значения времени - добавляем смещение 0.05 секунды...")
            
            # Создаем копию данных для обработки
            processed_df = df.copy()
            
            # Добавляем смещение 0.05 секунды к повторяющимся точкам
            shift_amount = 0.05  # пять сотых секунды
            
            for i in range(1, len(processed_df)):
                if processed_df.loc[i, 'Time'] <= processed_df.loc[i-1, 'Time']:
                    # Находим базовое время для этой группы повторений
                    base_time = processed_df.loc[i-1, 'Time']
                    
                    # Считаем сколько раз это время уже повторялось
                    repeat_count = 0
                    j = i - 1
                    while j >= 0 and processed_df.loc[j, 'Time'] == base_time:
                        repeat_count += 1
                        j -= 1
                    
                    # Добавляем смещение: 0.05, 0.10, 0.15 и т.д.
                    processed_df.loc[i, 'Time'] = base_time + (repeat_count * shift_amount)
            
            print(f"📝 Добавлено смещение: {shift_amount} секунды к повторяющимся точкам")
            
            # Усредняем данные с скользящим средним
            window_size = min(5, len(processed_df) // 10)
            if window_size < 3:
                window_size = 3
                
            processed_df['Smoothed'] = processed_df['SensorValue'].rolling(
                window=window_size, center=True, min_periods=1
            ).mean()
            
            # Сохраняем обработанные данные
            processed_df[['Time', 'Smoothed']].to_csv(processed_data_file, index=False, header=False)
            print(f"💾 Обработанные данные сохранены: {processed_data_file.name}")
            
            # Создаем график с обработанными данными
            create_gnuplot_plot(processed_data_file, output_file, processed_df, shift_amount, base_name)
            
        else:
            print("✅ Время уникально, просто сглаживаем данные...")
            # Просто сглаживаем данные
            df['Smoothed'] = df['SensorValue'].rolling(
                window=5, center=True, min_periods=1
            ).mean()
            
            df[['Time', 'Smoothed']].to_csv(smoothed_data_file, index=False, header=False)
            print(f"💾 Сглаженные данные сохранены: {smoothed_data_file.name}")
            
            create_gnuplot_plot(smoothed_data_file, output_file, df, 0, base_name)
            
    except Exception as e:
        print(f"❌ Ошибка обработки: {e}")
        return False

def create_gnuplot_plot(data_file, output_file, df, shift_amount, base_name):
    """Создает график через gnuplot"""
    try:
        # Определяем диапазоны для красивого отображения
        time_range = f"[{df['Time'].min():.2f}:{df['Time'].max():.2f}]"
        value_range = f"[{df['SensorValue'].min() * 0.9:.2f}:{df['SensorValue'].max() * 1.1:.2f}]"
        
        title = f"Обработанные данные: {base_name}"
        if shift_amount > 0:
            title += f" (смещение: {shift_amount}s)"
        
        gnuplot_script = f"""
set terminal png enhanced size 1400,800
set output "{output_file}"
set title "{title}"
set xlabel "Time (s)"
set ylabel "SensorValue"
set grid xtics ytics
set key top left

# Диапазоны для лучшего отображения
set xrange {time_range}
set yrange {value_range}

# Настройки данных
set datafile separator ","

# Рисуем сглаженную линию
plot "{data_file}" using 1:2 with lines lw 3 lc rgb "blue" title "Сглаженные данные"

set print "-"
print "График создан: {output_file}"
"""
        
        result = subprocess.run(
            ['gnuplot'],
            input=gnuplot_script,
            text=True,
            capture_output=True,
            timeout=30
        )
        
        if output_file.exists():
            print(f"✅ График создан: {output_file.name}")
            print(f"📊 Новый диапазон времени: {df['Time'].min():.2f} - {df['Time'].max():.2f} s")
            
    except Exception as e:
        print(f"❌ Ошибка gnuplot: {e}")

def show_detailed_time_analysis(filename):
    """Детальный анализ временных данных"""
    script_dir = Path(__file__).parent.absolute()
    data_file = script_dir / filename
    
    try:
        df = pd.read_csv(data_file, header=None, names=['Time', 'SensorValue'])
        
        print("📋 ДЕТАЛЬНЫЙ АНАЛИЗ ВРЕМЕНИ:")
        print(f"Всего записей: {len(df)}")
        print(f"Уникальных времен: {df['Time'].nunique()}")
        
        # Находим повторяющиеся времена
        time_counts = df['Time'].value_counts()
        repeated_times = time_counts[time_counts > 1]
        
        if len(repeated_times) > 0:
            print(f"\n🔍 Повторяющиеся значения времени:")
            for time_val, count in repeated_times.head(5).items():
                print(f"  Время {time_val:.2f}s повторяется {count} раз")
            
            if len(repeated_times) > 5:
                print(f"  ... и еще {len(repeated_times) - 5} повторяющихся времен")
        
    except Exception as e:
        print(f"❌ Ошибка анализа: {e}")

def cleanup_old_files(base_name):
    """Удаляет старые файлы с тем же базовым именем"""
    script_dir = Path(__file__).parent.absolute()
    
    files_to_remove = [
        f"{base_name}_processed.png",
        f"{base_name}_processed.txt", 
        f"{base_name}_smoothed.txt"
    ]
    
    print("🧹 Очистка старых файлов...")
    for file_name in files_to_remove:
        file_path = script_dir / file_name
        if file_path.exists():
            try:
                file_path.unlink()
                print(f"  Удален: {file_name}")
            except:
                pass

# Запуск
if __name__ == "__main__":
    print("=" * 70)
    print("🎯 КОРРЕКЦИЯ ВРЕМЕНИ - СМЕЩЕНИЕ НА 0.05 СЕКУНДЫ")
    print("=" * 70)
    
    # Получаем название файла от пользователя
    data_filename = get_filename_from_user()
    if data_filename is None:
        exit()
    
    base_name = Path(data_filename).stem
    
    # Очищаем старые файлы
    cleanup_old_files(base_name)
    
    # Детальный анализ
    show_detailed_time_analysis(data_filename)
    
    print("\n" + "=" * 70)
    print(f"🛠️  НАЧИНАЕМ ОБРАБОТКУ ФАЙЛА: {data_filename}")
    print("=" * 70)
    
    # Обрабатываем и создаем график
    process_and_create_plot(data_filename)
    
    print("\n" + "=" * 70)
    print("✅ ОБРАБОТКА ЗАВЕРШЕНА")
    print("=" * 70)
    
    # Показываем созданные файлы
    script_dir = Path(__file__).parent.absolute()
    print("📁 СОЗДАННЫЕ ФАЙЛЫ:")
    created_files = list(script_dir.glob(f"{base_name}_*"))
    
    if created_files:
        for file in created_files:
            if file.exists():
                size_kb = file.stat().st_size / 1024
                print(f"  📊 {file.name} ({size_kb:.1f} KB)")
    else:
        print("  ❌ Файлы не были созданы")
    
    print("\n🎯 Готово! Можно обработать другдой файл, запустив программу снова.")