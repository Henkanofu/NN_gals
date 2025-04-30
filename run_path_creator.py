from lib_path_creator import PolygonProcessor

# Создание процессора с настройками
processor = PolygonProcessor(
    image_scale_x=3.0,
    image_scale_y=2.0,
    brush_radius=0.05,
    split_lines_x=[1.0, 2.0]  # Опциональные разделительные линии
)

# Загрузка и обработка данных
polygons = processor.parse_data('/home/ubuntu22/Desktop/Oceanos_work/NN_gals/example_lables/f2_272_jpg.rf.eaa2f76967d218701b50317d4ad0292c.txt')
split_polygons, points_data = processor.process_polygons(polygons, processor.brush_radius)

# Визуализация
processor.plot_results(split_polygons, processor.brush_radius, points_data, output_file='result.png')