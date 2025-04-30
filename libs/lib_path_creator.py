"""
polygon_processing.py - модуль для обработки полигонов и генерации траекторий
"""

import numpy as np
import matplotlib.pyplot as plt
from shapely.geometry import Polygon, LineString, MultiPolygon
from shapely.ops import split
from typing import List, Tuple, Dict, Optional, Union


class PolygonProcessor:
    """Класс для обработки полигонов и генерации траекторий"""
    
    def __init__(self, 
                 image_scale_x: float = 3.0, 
                 image_scale_y: float = 2.0, 
                 brush_radius: float = 0.1,
                 split_lines_x: Optional[List[float]] = None):
        """
        Инициализация процессора полигонов
        
        Args:
            image_scale_x: Масштаб для оси X (пиксели в метры)
            image_scale_y: Масштаб для оси Y (пиксели в метры)
            brush_radius: Радиус щетки по умолчанию (в метрах)
            split_lines_x: X-координаты разделительных линий (в метрах)
        """
        self.image_scale_x = image_scale_x
        self.image_scale_y = image_scale_y
        self.brush_radius = brush_radius
        self.new_points_data = []  # Для хранения данных о точках
        
        if split_lines_x is None:
            self.split_lines_x = [image_scale_x/3, (image_scale_x/3)*2]
        else:
            self.split_lines_x = sorted(split_lines_x)
    
    @staticmethod
    def unique_points(points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Удаляет дубликаты точек с сохранением порядка"""
        seen = set()
        return [p for p in points if not (p in seen or seen.add(p))]
    
    def ensure_minimum_points(self, polygon_points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Добавляет точки в полигон, если их меньше двух"""
        if len(polygon_points) >= 2:
            return polygon_points
        
        # Получаем границы полигона
        minx = min(p[0] for p in polygon_points) if polygon_points else 0
        maxx = max(p[0] for p in polygon_points) if polygon_points else 0
        miny = min(p[1] for p in polygon_points) if polygon_points else 0
        maxy = max(p[1] for p in polygon_points) if polygon_points else 0
        
        # Среднее по X
        mid_x = (minx + maxx) / 2
        
        # Если нет точек вообще - создаем две
        if len(polygon_points) == 0:
            return [(mid_x, miny), (mid_x, maxy)]
        
        # Если только одна точка - добавляем вторую
        if len(polygon_points) == 1:
            existing_point = polygon_points[0]
            if existing_point[1] > (miny + maxy) / 2:  # Если точка в верхней части
                return [existing_point, (mid_x, miny)]
            else:  # Если точка в нижней части
                return [existing_point, (mid_x, maxy)]
        
        return polygon_points
    
    def adjust_last_point(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Корректирует последнюю точку маршрута, выравнивая её по Y с точкой за две позиции до неё"""
        if len(points) < 4:  # Нужно как минимум 4 точки для корректировки
            return points
        
        last_point = points[-1]
        reference_point = points[-4]  # Точка за три позиции до последней (так как индексы с 0)
        roll_point = points[-2]
        
        # Получаем y-координаты для сравнения
        last_y = last_point[1]
        ref_y = reference_point[1]
        roll_y = roll_point[1]
        
        if last_y > roll_y:  # точка снизу 
            if last_y > ref_y:
                return points
            else:
                adjusted_point = (last_point[0], ref_y)
        else: # точка сверху 
            if last_y > ref_y:
                adjusted_point = (last_point[0], ref_y)
            else:
                return points
                
        # Заменяем последнюю точку на скорректированную
        return points[:-1] + [adjusted_point]
    
    def process_coordinates(self, path: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Обрабатывает координаты пути, добавляя дополнительные точки"""
        x = 0
        if not path:
            return []
        
        path = self.unique_points(path)
        processed = [path[0]]
        
        for i in range(1, len(path), 2):
            if i + 1 >= len(path):
                processed.append(path[i])
                break
                
            point1, point2 = path[i], path[i + 1]
            x += 1
            
            if x % 2 == 1:
                y_val = point1[1] if point1[1] > point2[1] else point2[1]
                processed.extend([(point1[0], y_val), (point2[0], y_val)])
            else:
                y_val = point1[1] if point1[1] < point2[1] else point2[1]
                processed.extend([(point1[0], y_val), (point2[0], y_val)])
        
        # Применяем корректировку последней точки
        processed = self.adjust_last_point(processed)
        
        return processed
    
    def parse_data(self, file_path: str) -> List[Polygon]:
        """Парсит данные из файла и возвращает список полигонов"""
        polygons = []
        current_polygon = []
        
        with open(file_path, 'r') as file:
            for line in file:
                if not line.strip(): continue
                data = line.strip().split()[1:]
                if not data: continue
                
                coords = list(map(float, data))
                # Масштабируем координаты с использованием отдельных масштабов для X и Y
                coords_scaled = []
                for i in range(0, len(coords), 2):
                    coords_scaled.append(coords[i] * self.image_scale_x)   # X координата
                    coords_scaled.append(coords[i+1] * self.image_scale_y) # Y координата
                current_polygon.extend(zip(coords_scaled[::2], coords_scaled[1::2]))
                
                if line.startswith('0'):
                    if current_polygon:
                        # Обеспечиваем минимальное количество точек
                        current_polygon = self.ensure_minimum_points(current_polygon)
                        polygons.append(Polygon(current_polygon))
                        current_polygon = []
        
        if current_polygon:
            current_polygon = self.ensure_minimum_points(current_polygon)
            polygons.append(Polygon(current_polygon))
        
        return polygons
    
    def create_vertical_lines(self, polygon: Polygon, brush_radius: float) -> List[LineString]:
        """Создает вертикальные линии для заданного полигона"""
        minx, miny, maxx, maxy = polygon.bounds
        lines = []
        x = minx
        while x <= maxx:
            line = LineString([(x, miny), (x, maxy)])
            intersection = polygon.intersection(line)
            if intersection.is_empty:
                x += brush_radius
                continue
            if intersection.geom_type == 'MultiLineString':
                for geom in intersection.geoms:
                    lines.append(geom)
            elif intersection.geom_type == 'LineString':
                lines.append(intersection)
            x += brush_radius
        return lines
    
    def split_polygon_with_lines(self, polygon: Polygon) -> List[Polygon]:
        """Разделяет полигон вертикальными линиями"""
        result = [polygon]
        
        for split_x in self.split_lines_x:
            split_line = LineString([(split_x, polygon.bounds[1]), (split_x, polygon.bounds[3])])
            temp = []
            
            for geom in result:
                if geom.geom_type not in ['Polygon', 'MultiPolygon']:
                    continue
                    
                if geom.intersects(split_line):
                    try:
                        parts = split(geom, split_line)
                        if parts.geom_type == 'MultiPolygon':
                            temp.extend(parts.geoms)
                        elif parts.geom_type == 'GeometryCollection':
                            for part in parts.geoms:
                                if part.geom_type == 'Polygon':
                                    temp.append(part)
                        else:
                            temp.append(parts)
                    except:
                        temp.append(geom)
                else:
                    temp.append(geom)
            result = temp
        
        return [geom for geom in result if geom.geom_type == 'Polygon' and not geom.is_empty]
    
    def determine_section(self, polygon: Polygon) -> str:
        """Определяет секцию полигона (Left, Middle, Right)"""
        minx, _, maxx, _ = polygon.bounds
        if maxx <= self.split_lines_x[0]:
            return "Left"
        elif minx >= self.split_lines_x[-1]:
            return "Right"
        else:
            return "Middle"
    
    def generate_snake_path(self, points: List[Tuple[float, float]], brush_radius: float) -> List[Tuple[float, float]]:
        """Генерирует змеевидный путь для заданных точек"""
        if len(points) < 2:
            return []
        
        points = self.unique_points(points)
        
        upper = []
        lower = []
        for i in range(0, len(points), 2):
            if i+1 < len(points):
                lower.append(points[i])
                upper.append(points[i+1])
        
        path = []
        for i in range(len(upper)):
            if i % 2 == 0:
                path.append(lower[i])
                path.append(upper[i])
            else:
                path.append(upper[i])
                path.append(lower[i])
            
            if i < len(upper)-1:
                if i % 2 == 0:
                    path.append((upper[i][0], upper[i][1]))
                else:
                    path.append((lower[i][0], lower[i][1]))
        
        return path
    
    def process_polygons(self, polygons: List[Polygon], brush_radius: float) -> Tuple[List[Polygon], List[Tuple[str, int, List[Tuple[float, float]]]]]:
        """Обрабатывает список полигонов и генерирует точки для траекторий"""
        self.new_points_data = []  # Очищаем предыдущие данные
        split_polygons = []
        
        for polygon in polygons:
            split_polygons.extend(self.split_polygon_with_lines(polygon))
        
        for polygon_idx, polygon in enumerate(split_polygons):
            lines = self.create_vertical_lines(polygon, brush_radius)
            points = []
            
            for line in lines:
                coords = list(line.coords)
                points.extend(coords)
            
            if not points:
                continue
                
            grouped = {}
            for x, y in points:
                if x not in grouped:
                    grouped[x] = []
                grouped[x].append(y)
            
            vertical_points = []
            for x in sorted(grouped.keys()):
                ys = sorted(grouped[x])
                vertical_points.append((x, ys[0]))
                vertical_points.append((x, ys[-1]))
            
            section = self.determine_section(polygon)
            self.new_points_data.append((section, polygon_idx + 1, vertical_points))
        
        return split_polygons, self.new_points_data

    def panel_generate_protocol(self, direction: str) -> str:
        """
        Генерирует протокол перемещения в формате NMEA
        
        Args:
            direction: Направление для фильтрации ('Panel_1', 'Object_all' или конкретная секция)
        
        Returns:
            Строка с протоколом в формате NMEA
        """
        protocol_lines = []
        total_points = 0
        total_objects = 0
        object_number = 1  # Инициализация номера объекта

        for section, poly_idx, points in self.new_points_data:
            # Фильтрация по направлению
            if direction == 'Object_all':
                pass  # Берем все объекты
            elif direction == 'Panel_1':
                if section not in ['Left', 'Middle', 'Right']:
                    continue
            elif section != direction:
                continue
            
            original_path = self.generate_snake_path(points, self.brush_radius)
            if not original_path:
                continue
            
            processed_path = self.process_coordinates(original_path)
            if not processed_path:
                continue
            
            total_objects += 1
            num_points = len(processed_path)
            total_points += num_points
            
            # Теперь передаем только номер объекта, количество точек и координаты
            protocol_line = f"{object_number},{num_points}," + \
                        ",".join(f"{x:.3f},{y:.3f}" for x, y in processed_path)
            protocol_lines.append(protocol_line)
            object_number += 1

        if not protocol_lines:
            return f"No data for direction: {direction}"

        # Формируем финальный протокол (brush_radius указывается только один раз в начале)
        protocol = f"$PNLMV,{self.brush_radius:.3f},{total_points},{total_objects}," + \
                ",".join(protocol_lines)

        # Генерация контрольной суммы NMEA
        checksum_data = protocol[1:]  # Берем все после '$'
        checksum = 0
        for c in checksum_data:
            checksum ^= ord(c)
        protocol += f"*{checksum:02X}"

        return protocol
    
    def plot_results(self, 
                    polygons: List[Polygon], 
                    brush_radius: float, 
                    new_points_data: List[Tuple[str, int, List[Tuple[float, float]]]],
                    output_file: Optional[str] = None):
        """Визуализирует результаты обработки полигонов"""
        fig, ax = plt.subplots(figsize=(14, 10))
        colors = plt.get_cmap('tab20', len(polygons))
        
        for i, polygon in enumerate(polygons):
            if polygon.geom_type == 'Polygon' and not polygon.is_empty:
                x, y = polygon.exterior.xy
                ax.plot(x, y, color=colors(i), linewidth=1, alpha=0.5)
                ax.fill(x, y, color=colors(i), alpha=0.1)
        
        # Рисуем разделительные линии
        for split_x in self.split_lines_x:
            ax.axvline(x=split_x, color='green', linestyle='--', linewidth=2)
        
        for i, (section, poly_idx, points) in enumerate(new_points_data):
            if not points: continue
            
            original_path = self.generate_snake_path(points, brush_radius)
            processed_path = self.process_coordinates(original_path)
            
            if len(processed_path) > 1:
                x, y = zip(*processed_path)
                ax.plot(x, y, color=colors(i), linestyle='-', linewidth=2)
            
            for j, (x_p, y_p) in enumerate(processed_path):
                color = 'red' if j == 0 else 'blue'
                ax.scatter(x_p, y_p, color=color, s=100 if j == 0 else 80,
                           marker='o', edgecolors='black', linewidths=0.8)
        
        ax.set_aspect('equal')
        plt.xlabel('X (meters)')
        plt.ylabel('Y (meters)')
        plt.title(f'Processed Path (Brush: {brush_radius} meters, X-Scale: {self.image_scale_x}x, Y-Scale: {self.image_scale_y}x)')
        plt.grid(True, alpha=0.3)
        plt.gca().invert_yaxis()
        plt.tight_layout()
        
        if output_file:
            plt.savefig(output_file)
        else:
            plt.show()

def main():
    """Пример использования библиотеки с генерацией протокола"""
    processor = PolygonProcessor(
        image_scale_x=3.0,
        image_scale_y=2.0,
        brush_radius=0.1,
        split_lines_x=None
    )
    
    file_path = 'example_lables/f1_2548_jpg.rf.7d77275da2f422ff8ba33f6b327cb249.txt'
    
    polygons = processor.parse_data(file_path)
    split_polygons, new_points_data = processor.process_polygons(polygons, processor.brush_radius)

    if split_polygons:
        processor.plot_results(split_polygons, processor.brush_radius, new_points_data)
        
        # Вывод координат в консоль
        for section, poly_idx, points in new_points_data:
            original_path = processor.generate_snake_path(points, processor.brush_radius)
            if not original_path: continue
            
            processed_path = processor.process_coordinates(original_path)
            coords_str = " ".join(f"({x:.3f};{y:.3f})" for x, y in processed_path)
            print(f"{poly_idx} {section} {len(processed_path)} {processor.brush_radius} {coords_str}")
        
        # Генерация и вывод протоколов
        print("\nGenerated Protocols:")

        print("\nLeft Section Protocol:")
        print(processor.panel_generate_protocol("Middle"))
        
    else:
        print("Нет полигонов для отображения")


if __name__ == "__main__":
    main()

