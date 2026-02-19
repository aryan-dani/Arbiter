import { useMemo } from 'react';

const AXES = ['Speed', 'Efficiency', 'Accuracy', 'Coverage', 'Reliability'];
const AXIS_COUNT = AXES.length;
const CX = 100;
const CY = 100;
const RADIUS = 70;
const GRID_LEVELS = [25, 50, 75, 100];

function polarToCart(angleDeg, radius) {
  const rad = (angleDeg - 90) * (Math.PI / 180);
  return {
    x: CX + radius * Math.cos(rad),
    y: CY + radius * Math.sin(rad),
  };
}

function getAngle(i) {
  return (360 / AXIS_COUNT) * i;
}

export default function RadarChart({ values = {} }) {
  const gridPolygons = useMemo(() => {
    return GRID_LEVELS.map((level) => {
      const r = (level / 100) * RADIUS;
      const points = Array.from({ length: AXIS_COUNT }, (_, i) => {
        const { x, y } = polarToCart(getAngle(i), r);
        return `${x},${y}`;
      }).join(' ');
      return points;
    });
  }, []);

  const axisLines = useMemo(() => {
    return Array.from({ length: AXIS_COUNT }, (_, i) => {
      const { x, y } = polarToCart(getAngle(i), RADIUS);
      return { x1: CX, y1: CY, x2: x, y2: y };
    });
  }, []);

  const dataPoints = useMemo(() => {
    return AXES.map((axis, i) => {
      const val = values[axis.toLowerCase()] ?? 0;
      const r = (val / 100) * RADIUS;
      return polarToCart(getAngle(i), r);
    });
  }, [values]);

  const dataPolygon = dataPoints.map((p) => `${p.x},${p.y}`).join(' ');

  const labels = useMemo(() => {
    return AXES.map((axis, i) => {
      const { x, y } = polarToCart(getAngle(i), RADIUS + 18);
      return { text: axis, x, y };
    });
  }, []);

  return (
    <svg viewBox="0 0 200 200" className="w-full max-w-[220px] mx-auto">
      {/* Grid pentagons */}
      {gridPolygons.map((points, i) => (
        <polygon
          key={i}
          points={points}
          fill="none"
          stroke="#30363D"
          strokeWidth="0.8"
        />
      ))}

      {/* Axis lines */}
      {axisLines.map((line, i) => (
        <line
          key={i}
          x1={line.x1}
          y1={line.y1}
          x2={line.x2}
          y2={line.y2}
          stroke="#30363D"
          strokeWidth="0.6"
        />
      ))}

      {/* Data polygon - fill */}
      <polygon
        points={dataPolygon}
        fill="rgba(159, 39, 8, 0.2)"
        stroke="#C43A15"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />

      {/* Data dots */}
      {dataPoints.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r="3" fill="#C43A15" stroke="#0B0808" strokeWidth="1" />
      ))}

      {/* Level labels - just center numbers */}
      {GRID_LEVELS.map((level) => {
        const { x, y } = polarToCart(0, (level / 100) * RADIUS);
        return (
          <text
            key={level}
            x={x + 4}
            y={y + 1}
            fontSize="6"
            fill="#484F58"
            textAnchor="start"
          >
            {level}
          </text>
        );
      })}

      {/* Axis labels */}
      {labels.map((l, i) => (
        <text
          key={i}
          x={l.x}
          y={l.y}
          fontSize="8"
          fill="#8B949E"
          textAnchor="middle"
          dominantBaseline="central"
          fontWeight="500"
        >
          {l.text}
        </text>
      ))}
    </svg>
  );
}
