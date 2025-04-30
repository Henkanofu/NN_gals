from libs.lib_path_creator import PolygonProcessor  # Импортируем класс
import argparse
import os

def main():
    # Настройка парсера аргументов командной строки
    parser = argparse.ArgumentParser(description='Обработка полигонов и генерация протоколов')
    parser.add_argument('input_file', help='Путь к входному файлу с полигонами')
    parser.add_argument('--output', help='Путь для сохранения графика (опционально)')
    parser.add_argument('--protocol', choices=['Panel_1', 'Left', 'Middle', 'Right', 'Object_all'], 
                       default='Panel_1', help='Тип генерируемого протокола')
    args = parser.parse_args()

    # Проверка существования файла
    if not os.path.exists(args.input_file):
        print(f"Ошибка: файл {args.input_file} не найден")
        return

    # Инициализация процессора
    processor = PolygonProcessor(
        image_scale_x=3.0,
        image_scale_y=2.0,
        brush_radius=0.1,
        split_lines_x=None
    )
    
    # Обработка данных
    polygons = processor.parse_data(args.input_file)
    split_polygons, new_points_data = processor.process_polygons(polygons, processor.brush_radius)

    if not split_polygons:
        print("Нет полигонов для отображения")
        return

    # Визуализация результатов
    if args.output:
        processor.plot_results(split_polygons, processor.brush_radius, new_points_data, args.output)
    else:
        processor.plot_results(split_polygons, processor.brush_radius, new_points_data)
    
    # Вывод информации о точках
    for section, poly_idx, points in new_points_data:
        original_path = processor.generate_snake_path(points, processor.brush_radius)
        if not original_path: continue
        
        processed_path = processor.process_coordinates(original_path)
        coords_str = " ".join(f"({x:.3f};{y:.3f})" for x, y in processed_path)
        print(f"{poly_idx} {section} {len(processed_path)} {processor.brush_radius} {coords_str}")
    
    # Генерация и вывод протокола
    print("\nGenerated Protocol:")
    protocol = processor.generate_protocol(args.protocol)
    print(protocol)

if __name__ == "__main__":
    main()