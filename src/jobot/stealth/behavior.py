import math
import random
import time
from typing import List, Tuple


class BehavioralMimicry:
    """
    Behavioral Anti-Detection Engine (Layer F).
    Generates human-like Bezier curve mouse trajectories, keystroke dynamics, and scroll physics.
    """

    @staticmethod
    def generate_bezier_curve(
        start: Tuple[int, int], end: Tuple[int, int], control_points_count: int = 2
    ) -> List[Tuple[int, int]]:
        """Generate Cubic Bezier curve points with human-like jitter between start and end coordinates."""
        x1, y1 = start
        x2, y2 = end

        # Generate 2 control points offset from straight line
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        ctrl1_x = x1 + (mid_x - x1) * random.uniform(0.1, 0.5) + random.randint(-50, 50)
        ctrl1_y = y1 + (mid_y - y1) * random.uniform(0.1, 0.5) + random.randint(-50, 50)
        ctrl2_x = mid_x + (x2 - mid_x) * random.uniform(0.5, 0.9) + random.randint(-50, 50)
        ctrl2_y = mid_y + (y2 - mid_y) * random.uniform(0.5, 0.9) + random.randint(-50, 50)

        points = []
        steps = random.randint(25, 45)
        for i in range(steps + 1):
            t = i / steps
            # True 4-point Cubic Bezier interpolation
            x = (1 - t) ** 3 * x1 + 3 * (1 - t) ** 2 * t * ctrl1_x + 3 * (1 - t) * (t ** 2) * ctrl2_x + (t ** 3) * x2
            y = (1 - t) ** 3 * y1 + 3 * (1 - t) ** 2 * t * ctrl1_y + 3 * (1 - t) * (t ** 2) * ctrl2_y + (t ** 3) * y2
            # Add sub-pixel jitter to intermediate path points only
            if 0 < i < steps:
                x += random.uniform(-1.5, 1.5)
                y += random.uniform(-1.5, 1.5)
            points.append((int(x), int(y)))
        return points

    @staticmethod
    def get_keystroke_delays(text: str) -> List[float]:
        """Generate human-like typing inter-key delays (70ms - 220ms with pause on punctuation)."""
        delays = []
        for char in text:
            if char in ".,!?":
                delays.append(random.uniform(0.3, 0.6))  # Longer pause on punctuation
            elif char == " ":
                delays.append(random.uniform(0.15, 0.35))
            else:
                delays.append(random.uniform(0.07, 0.22))
        return delays
