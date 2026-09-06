// The workbench shipped with no visualisation at all, and its generic result
// renderer printed the literal string '已提供' for any nested object -- so every
// analysis page showed a row of labels and no data. These tests assert values
// actually reach the DOM, because "it builds" was exactly what was true while
// the page showed nothing.
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { BarChart, Donut, GroupedBars, LineChart, nice } from './charts';

describe('BarChart', () => {
  it('renders a labelled bar per usable value', () => {
    render(<BarChart title="獲利能力 (%)" data={[['毛利率', 23.16], ['營業利益率', 14.25]]} />);
    expect(screen.getByText('毛利率')).toBeInTheDocument();
    expect(screen.getByText('23.16%')).toBeInTheDocument();
    expect(screen.getByText('14.25%')).toBeInTheDocument();
  });

  it('drops absent values instead of drawing them as zero', () => {
    // A missing field is not a zero. Charting null as 0 would make an absent
    // margin look like a company that earned nothing.
    const { container } = render(<BarChart title="t" data={[['有', 10], ['無', null]]} />);
    expect(container.querySelectorAll('.bar-row')).toHaveLength(1);
    expect(screen.queryByText('無')).not.toBeInTheDocument();
  });

  it('puts a negative bar on the other side of zero', () => {
    const { container } = render(<BarChart title="t" data={[['投資現金流', -3389344], ['營運現金流', 14081773]]} unit="" />);
    const fills = container.querySelectorAll<HTMLElement>('.bar-fill');
    expect(fills).toHaveLength(2);
    expect(parseFloat(fills[0].style.left)).toBeLessThan(parseFloat(fills[1].style.left));
  });

  it('says why it is empty rather than rendering blank space', () => {
    render(<BarChart title="報酬率" data={[['ROA', null], ['ROE', null]]} />);
    expect(screen.getByText(/沒有可繪製的數值/)).toBeInTheDocument();
  });
});

describe('Donut', () => {
  it('renders one arc per part with its share', () => {
    const { container } = render(<Donut title="資本結構" data={[['負債', 15971430], ['權益', 41607063]]} />);
    expect(container.querySelectorAll('circle')).toHaveLength(2);
    // 15,971,430 / 57,578,493 = 27.7%
    expect(screen.getByText('27.7%')).toBeInTheDocument();
    expect(screen.getByText('72.3%')).toBeInTheDocument();
  });
});

describe('LineChart', () => {
  it('plots every period and carries the real values in tooltips', () => {
    const { container } = render(<LineChart
      title="Net Revenue"
      periods={['2024Q1', '2024Q2', '2025Q1']}
      series={[{ name: 'Net Revenue', values: [10489988, 13581755, 10484855] }]}
    />);
    expect(screen.getByText('2024Q1')).toBeInTheDocument();
    expect(screen.getByText('2025Q1')).toBeInTheDocument();
    // Queried directly rather than with getByTitle, which only matches a
    // <title> that is a direct child of <svg>; these hang off each <circle>.
    const titles = Array.from(container.querySelectorAll('title')).map(t => t.textContent);
    expect(titles).toContain('Net Revenue 2025Q1: 10,484,855');
    expect(titles).toContain('Net Revenue 2024Q1: 10,489,988');
  });

  it('breaks the line at a gap instead of interpolating over it', () => {
    // Interpolating across a missing period invents a figure for a quarter the
    // producer never reported.
    const { container } = render(<LineChart
      title="t" periods={['a', 'b', 'c']}
      series={[{ name: 's', values: [1, null, 3] }]}
    />);
    expect(container.querySelectorAll('polyline')[0].getAttribute('points')!.split(' ')).toHaveLength(2);
    expect(container.querySelectorAll('circle')).toHaveLength(2);
  });
});

describe('GroupedBars', () => {
  it('renders each company against each metric', () => {
    render(<GroupedBars
      title="同業指標比較"
      categories={['Gross Margin (%)']}
      series={[{ name: '3661', values: [23.16] }, { name: '2330', values: [58.79] }]}
    />);
    expect(screen.getByText('3661')).toBeInTheDocument();
    expect(screen.getByText('58.79%')).toBeInTheDocument();
  });

  it('shows a dash where a peer has no value for a metric', () => {
    render(<GroupedBars title="t" categories={['m']} series={[{ name: 'a', values: [1] }, { name: 'b', values: [null] }]} unit="" />);
    expect(screen.getByText('—')).toBeInTheDocument();
  });
});

describe('nice', () => {
  it('rounds an axis maximum up to a readable step', () => {
    expect(nice(23.16)).toBe(25);
    expect(nice(0)).toBe(1);
    expect(nice(58.79)).toBe(100);
  });
});
