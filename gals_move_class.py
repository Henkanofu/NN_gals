import numpy as np
import matplotlib.pyplot as plt
from shapely.geometry import Polygon, LineString, MultiPolygon
from shapely.ops import split
from typing import List, Tuple, Dict, Union

class PolygonProcessor:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.polygons = []
        self.split_polygons = []
        self.brush_radius = None
        self.new_points_data = []
        
    @staticmethod
    def unique_points(points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        seen = set()
        return [p for p in points if not (p in seen or seen.add(p))]
    
    @staticmethod
    def process_coordinates(path: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        if not path:
            return []
        
        path = PolygonProcessor.unique_points(path)
        processed = [path[0]]
        x = 0
        
        for i in range(1, len(path), 2):
            if i + 1 >= len(path):
                processed.append(path[i])
                break
                
            point1, point2 = path[i], path[i + 1]
            x += 1
            
            if x % 2 == 1:
                y_val = max(point1[1], point2[1])
                processed.extend([(point1[0], y_val), (point2[0], y_val)])
            else:
                y_val = min(point1[1], point2[1])
                processed.extend([(point1[0], y_val), (point2[0], y_val)])
        
        return processed
    
    def parse_data(self) -> None:
        current_polygon = []
        
        with open(self.file_path, 'r') as file:
            for line in file:
                if not line.strip(): 
                    continue
                data = line.strip().split()[1:]
                if not data: 
                    continue
                
                coords = list(map(float, data))
                current_polygon.extend(zip(coords[::2], coords[1::2]))
                
                if line.startswith('0'):
                    if current_polygon:
                        self.polygons.append(Polygon(current_polygon))
                        current_polygon = []
        
        if current_polygon:
            self.polygons.append(Polygon(current_polygon))
    
    def create_vertical_lines(self, polygon: Polygon) -> List[LineString]:
        minx, miny, maxx, maxy = polygon.bounds
        lines = []
        x = minx
        
        while x <= maxx:
            line = LineString([(x, miny), (x, maxy)])
            intersection = polygon.intersection(line)
            
            if intersection.is_empty:
                x += self.brush_radius
                continue
                
            if intersection.geom_type == 'MultiLineString':
                for geom in intersection.geoms:
                    lines.append(geom)
            elif intersection.geom_type == 'LineString':
                lines.append(intersection)
                
            x += self.brush_radius
            
        return lines
    
    def split_polygon_with_lines(self, polygon: Polygon) -> List[Polygon]:
        split_lines = [
            LineString([(0.5, polygon.bounds[1]), (0.5, polygon.bounds[3])]),
            LineString([(0.8, polygon.bounds[1]), (0.8, polygon.bounds[3])])
        ]
        
        result = [polygon]
        
        for split_line in split_lines:
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
    
    @staticmethod
    def determine_section(polygon: Polygon) -> str:
        minx, _, maxx, _ = polygon.bounds
        if maxx <= 0.5:
            return "Left"
        elif minx >= 0.8:
            return "Right"
        else:
            return "Middle"
    
    @staticmethod
    def generate_snake_path(points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        if len(points) < 2:
            return []
        
        points = PolygonProcessor.unique_points(points)
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
    
    def generate_protocol(self, direction: str) -> str:
        protocol_lines = []
        total_points = 0
        total_obstacles = 0
        object_number = 1  # Initialize object number       

        for section, poly_idx, points in self.new_points_data:
            if section == direction:
                original_path = self.generate_snake_path(points)
                if not original_path:
                    continue
                
                processed_path = self.process_coordinates(original_path)
                if not processed_path:
                    continue
                
                total_obstacles += 1
                num_points = len(processed_path)
                total_points += num_points
                
                protocol_line = f"{object_number},{num_points},{self.brush_radius:.3f}," + \
                ",".join(f"{x:.3f},{y:.3f}" for x, y in processed_path)
                protocol_lines.append(protocol_line)
                object_number += 1  # Increment object number for the next object

        if not protocol_lines:
            return f"No data for direction: {direction}"

        # Формируем финальный протокол
        protocol = f"$PNLMV,{total_points},{total_obstacles}," + \
                ",".join(protocol_lines)

        # Генерация контрольной суммы NMEA
        checksum_data = protocol[1:]  # Take everything after the '$'
        checksum = 0
        for c in checksum_data:
            checksum ^= ord(c)
        protocol += f"*{checksum:02X}"

        return protocol

    def process_polygons(self, brush_radius: float) -> None:
        self.brush_radius = brush_radius
        
        for polygon in self.polygons:
            self.split_polygons.extend(self.split_polygon_with_lines(polygon))
        
        for polygon_idx, polygon in enumerate(self.split_polygons):
            lines = self.create_vertical_lines(polygon)
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
    
    def plot_results(self) -> None:
        if not self.split_polygons:
            print("Нет полигонов для отображения")
            return
            
        fig, ax = plt.subplots(figsize=(14, 10))
        colors = plt.get_cmap('tab20', len(self.split_polygons))
        
        for i, polygon in enumerate(self.split_polygons):
            if polygon.geom_type == 'Polygon' and not polygon.is_empty:
                x, y = polygon.exterior.xy
                ax.plot(x, y, color=colors(i), linewidth=1, alpha=0.5)
                ax.fill(x, y, color=colors(i), alpha=0.1)
        
        ax.axvline(x=0.5, color='green', linestyle='--', linewidth=2)
        ax.axvline(x=0.8, color='green', linestyle='--', linewidth=2)
        
        for i, (section, poly_idx, points) in enumerate(self.new_points_data):
            if not points: 
                continue
            
            original_path = self.generate_snake_path(points)
            processed_path = self.process_coordinates(original_path)
            
            if len(processed_path) > 1:
                x, y = zip(*processed_path)
                ax.plot(x, y, color=colors(i), linestyle='-', linewidth=2)
            
            for j, (x_p, y_p) in enumerate(processed_path):
                color = 'red' if j == 0 else 'blue'
                ax.scatter(x_p, y_p, color=color, s=100 if j == 0 else 80,
                           marker='o', edgecolors='black', linewidths=0.8)
        
        ax.set_aspect('equal')
        plt.xlabel('X')
        plt.ylabel('Y')
        plt.title(f'Processed Path (Brush: {self.brush_radius})')
        plt.grid(True, alpha=0.3)
        plt.gca().invert_yaxis()
        plt.tight_layout()
        plt.show()
    
    def print_results(self) -> None:
        for section, poly_idx, points in self.new_points_data:
            original_path = self.generate_snake_path(points)
            if not original_path: 
                continue
            
            processed_path = self.process_coordinates(original_path)
            coords_str = " ".join(f"({x:.3f};{y:.3f})" for x, y in processed_path)
            print(f"{poly_idx} {section} {len(processed_path)} {self.brush_radius:.3f} {coords_str}")


if __name__ == "__main__":
    file_path = '/home/ubuntu22/Desktop/Oceanos_work/NN_gals/example_lables/f1_2743_jpg.rf.ec3e5370fe50a1bbfc33efd0626dcd8e.txt'
    processor = PolygonProcessor(file_path)
    processor.parse_data()
    
    brush_radius = float(input("Радиус щётки (например 0.1): "))
    processor.process_polygons(brush_radius)
    
    processor.plot_results()
    processor.print_results()
    
    user_input = input("Введите направление (Left, Middle, Right): ")
    protocol = processor.generate_protocol(user_input)
    print("\nСгенерированный протокол:")
    print(protocol)