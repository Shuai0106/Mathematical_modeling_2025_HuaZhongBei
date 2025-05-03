import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.widgets import Cursor
from collections import defaultdict
import re
from typing import List, Dict


# ===================== 数据模型 =====================
class TransportRoute:
    def __init__(self, start: str, end: str, action: str, quantity: int):
        self.start = start
        self.end = end
        self.action = action
        self.quantity = quantity

    @property
    def path(self) -> List[str]:
        return [self.start, self.end]

    def __repr__(self) -> str:
        return f"{self.start}→{self.end} [{self.action}×{self.quantity}]"


# ===================== 数据预处理 =====================
class CampusDataProcessor:
    _NODE_PATTERN = re.compile(r"([\u4e00-\u9fa5A-Za-z0-9_]+)\s*->\s*([\u4e00-\u9fa5A-Za-z0-9_]+)")
    _ACTION_PATTERN = re.compile(r"([^\d]+)(\d+)?")

    def __init__(self, nodes_config: Dict[str, tuple]):
        self.nodes = nodes_config
        self.flux = defaultdict(int)

    def parse_routes(self, data: str) -> List[TransportRoute]:
        routes = []
        for idx, line in enumerate(data.strip().split('\n'), 1):
            try:
                path_part, action_part = self._split_line_parts(line)
                start, end = self._parse_path(path_part)
                action, qty = self._parse_action(action_part)

                route = TransportRoute(start, end, action, qty)
                routes.append(route)
                self._update_flux(route)

            except ValueError as e:
                print(f"❗ 行 {idx} 解析失败: {line}\n   → 错误: {e}")
        return routes

    def _split_line_parts(self, line: str) -> tuple:
        if '(' in line and ')' in line:
            path_part = line[:line.index('(')].strip()
            action_part = line[line.index('(') + 1: line.index(')')].strip()
        else:
            path_part = line.strip()
            action_part = "移动 0"
        return path_part, action_part

    def _parse_path(self, text: str) -> tuple:
        match = self._NODE_PATTERN.search(text)
        if not match:
            raise ValueError("路径格式不符合规范")
        start, end = match.groups()
        return self._validate_node(start), self._validate_node(end)

    def _parse_action(self, text: str) -> tuple:
        parts = text.split()
        if len(parts) == 1:
            match = self._ACTION_PATTERN.fullmatch(parts[0])
            action = match.group(1) if match else parts[0]
            qty = int(match.group(2)) if match and match.group(2) else 0
        else:
            action, qty = parts[0], parts[-1]
        return action.strip(), int(qty) if str(qty).isdigit() else 0

    def _validate_node(self, node: str) -> str:
        if node not in self.nodes:
            raise ValueError(f"节点 '{node}' 未在坐标配置中定义")
        return node

    def _update_flux(self, route: TransportRoute):
        if route.action == "载取":
            self.flux[route.end] += route.quantity
        elif route.action == "运送":
            self.flux[route.start] -= route.quantity


# ===================== 可视化引擎 =====================
class CampusVisualizer:
    def __init__(self, size=(1280, 720), dpi=100):
        self.fig = plt.figure(figsize=(size[0] / dpi, size[1] / dpi),
                              dpi=dpi, facecolor='#F5F5F5')
        self.ax = self.fig.add_subplot(facecolor='#FAFAFA')
        self.min_x = 0
        self.max_x = 0
        self.min_y = 0
        self.max_y = 0
        self._init_style()

    def _init_style(self):
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
        plt.rcParams['axes.unicode_minus'] = False
        self._COLOR_MAP = {
            '载取': ('#E74C3C', '#FADBD8'),
            '运送': ('#3498DB', '#D6EAF8'),
            '移动': ('#2ECC71', '#D5F5E3')
        }
        self._CMAP = LinearSegmentedColormap.from_list(
            "flux", ['#2ECC71', '#F1C40F', '#E74C3C'])

    def visualize(self, processor: CampusDataProcessor,
                  routes: List[TransportRoute], title: str):
        self._calc_axis_range(processor.nodes)
        self._draw_base_map(processor.nodes)
        self._draw_flow_lines(processor.nodes, routes)
        self._draw_heat_layer(processor.flux, processor.nodes)
        self._setup_axis()
        self._setup_layout(title)
        self._add_interactive_features(processor, routes)
        plt.show()

    def _calc_axis_range(self, nodes: Dict[str, tuple]):
        all_x = [x for x, y in nodes.values()]
        all_y = [y for x, y in nodes.values()]
        padding = 15
        self.min_x = min(all_x) - padding
        self.max_x = max(all_x) + padding
        self.min_y = min(all_y) - padding
        self.max_y = max(all_y) + padding

    def _draw_base_map(self, nodes: Dict[str, tuple]):
        # 增大节点尺寸并强化标签
        nx.draw_networkx_nodes(nx.DiGraph(), nodes,
                             node_size=1200,
                             node_color='white',
                             edgecolors='#85929E',  # 加深边框颜色
                             linewidths=2.0,
                             ax=self.ax)
        # 关键修改：强化标签显示
        nx.draw_networkx_labels(nx.DiGraph(), nodes,
                              font_size=11,
                              font_family='Microsoft YaHei',
                              font_weight='bold',
                              font_color='#2E4053',  # 更深颜色
                              verticalalignment='center',
                              ax=self.ax)

    def _draw_flow_lines(self, nodes: Dict[str, tuple], routes: List[TransportRoute]):
        for route in routes:
            color, _ = self._COLOR_MAP.get(route.action, ('#95A5A6', '#EBEDEF'))
            max_qty = max(r.quantity for r in routes)
            linewidth = 1 + 3 * (route.quantity / max_qty if max_qty != 0 else 0)

            if route.start == route.end:
                self._draw_self_loop(nodes[route.start], color, linewidth, route)
            else:
                self._draw_directional_arrow(nodes[route.start], nodes[route.end], color, linewidth, route)

    def _draw_directional_arrow(self, start_pos: tuple, end_pos: tuple,
                                color: str, width: float, route: TransportRoute):
        arrowprops = {
            'arrowstyle': "fancy",
            'connectionstyle': "arc3,rad=0.25",
            'color': color,
            'linewidth': width,
            'shrinkA': 12,
            'shrinkB': 12,
            'alpha': 0.8
        }
        self.ax.annotate("", xy=end_pos, xytext=start_pos,
                         arrowprops=arrowprops, annotation_clip=False)

        mid_x = (start_pos[0] + end_pos[0]) / 2
        mid_y = (start_pos[1] + end_pos[1]) / 2
        self.ax.text(mid_x, mid_y, f"{route.action}×{route.quantity}",
                     color=color, fontsize=8, ha='center', va='center',
                     bbox=dict(boxstyle="round", alpha=0.9,
                               facecolor='white', edgecolor=color))

    def _draw_self_loop(self, pos: tuple, color: str, width: float, route: TransportRoute):
        self.ax.add_patch(plt.Circle((pos[0] + 3, pos[1] + 3), radius=2.5,
                                     color=color, alpha=0.6, fill=False,
                                     linewidth=width))
        self.ax.text(pos[0] + 5, pos[1] + 5, f"Loop {route.quantity}",
                     color=color, fontsize=7, rotation=45)

    def _draw_heat_layer(self, flux: Dict[str, int], nodes: Dict[str, tuple]):
        if not flux: return
        vmin, vmax = min(flux.values()), max(flux.values())
        norm_flux = {k: (v - vmin) / (vmax - vmin + 1e-8) for k, v in flux.items()}

        self.ax.set_zorder(2)  # 确保热力层在标签下方
        for node, value in norm_flux.items():
            x, y = nodes[node]
            # 减少半径并降低透明度
            radius = 3.5 + abs(value) * 20  # 原值：5.5 + abs(value)*45
            circle = plt.Circle((x, y), radius=radius,
                              color=self._CMAP(value),
                              alpha=0.12,  # 原值 0.15
                              zorder=1)    # 设置图层顺序
            self.ax.add_patch(circle)

    def _setup_axis(self):
        self.ax.set_aspect('equal')  # 新增：保持比例
        self.ax.set_xlim(self.min_x, self.max_x)
        self.ax.set_ylim(self.min_y, self.max_y)
        self.ax.margins(0.08)  # 新增：增加边距防止被裁剪
        self.ax.axis('off')

    def _setup_layout(self, title: str):
        self.ax.set_title(title, fontsize=16, pad=20, color='#2C3E50')
        self.fig.tight_layout(pad=3.0)

    def _add_interactive_features(self, processor: CampusDataProcessor,
                                  routes: List[TransportRoute]):
        cursor = Cursor(self.ax, useblit=True, color='#E74C3C', linewidth=1)
        annot = self.ax.annotate("", xy=(0, 0), xytext=(20, 20),
                                 textcoords="offset points",
                                 bbox=dict(boxstyle="round,pad=0.5",
                                           fc="white", ec="#BDC3C7",
                                           alpha=0.95))
        annot.set_visible(False)

        def on_hover(event):
            if not event.inaxes: return
            annot.set_visible(False)

            for node, (x, y) in processor.nodes.items():
                if abs(x - event.xdata) < 2 and abs(y - event.ydata) < 2:
                    related_routes = [r for r in routes if node in (r.start, r.end)][:3]

                    info_lines = [
                                     f"📌 {node}",
                                     f"📦 当前流量: {processor.flux.get(node, 0):+}",
                                     "━" * 14
                                 ] + [f"• {r.start}→{r.end} {r.action}×{r.quantity}"
                                      for r in related_routes] or ["暂无运输活动"]

                    annot.set_text("\n".join(info_lines))
                    annot.xy = (x, y)
                    annot.set_visible(True)
                    self.fig.canvas.draw_idle()
                    return

        self.fig.canvas.mpl_connect("motion_notify_event", on_hover)


# ===================== 配置数据 =====================
nodes = {
    '运维处': (85, 62), '菊苑1栋': (32, 43), '梅苑1栋': (38, 52),
    '计算机学院': (45, 29), '东门': (68, 12), '一食堂': (76, 24),
    '教学2楼': (92, 28), '工程中心': (105, 35), '南门': (48, 78),
    '二食堂': (64, 51), '教学4楼': (88, 44), '三食堂': (97, 58),
    '北门': (112, 12), '网球场': (116, 65), '体育馆': (124, 54)
}

input_data = """
运维处->菊苑1栋(载取20)
运维处 -> 菊苑1栋 （载取 20）
运维处 ->菊苑1栋(载取16)
菊苑1栋->梅苑1栋  (运送6)
梅苑1栋 -> 计算机学院 (运送 11)
计算机学院->东门(运送5)
东门->一食堂 ( 运送5 )
一食堂->教学2楼(运送 9)
教学2楼->教学2楼(运送11)
教学2楼->工程中心(运送9)
运维处->南门(载取20)
运维处 ->二食堂 ( 载取 20 )
二食堂->教学4楼(运送20)
教学4楼->三食堂(运送8)
运维处->二食堂(载取7)
二食堂->教学2楼(运送12)
教学2楼->工程中心(运送15)
工程中心->北门(运送7)
运维处->网球场(载取3)
运维处->体育馆(载取4)
体育馆->北门(运送3)
"""

# ===================== 主程序 =====================
if __name__ == "__main__":
    processor = CampusDataProcessor(nodes)
    routes = processor.parse_routes(input_data)

    print(f"✅ 成功解析 {len(routes)} 条有效路径")
    print("节点流量统计:")
    for node, flux in processor.flux.items():
        print(f"  {node}: {flux:+}")

    visualizer = CampusVisualizer()
    visualizer.visualize(
        processor=processor,
        routes=routes,
        title="智慧校园物流网络实时监控 - 09:00 AM"
    )
