import { useEffect, useRef } from 'react';
import { useOrderBook } from '@/hooks/useTrades';
import * as d3 from 'd3';
import './OrderBook.css';

interface OrderBookProps {
  symbol: string;
}

export function OrderBook({ symbol }: OrderBookProps) {
  const { orderBook } = useOrderBook(symbol);
  const chartRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!orderBook || !chartRef.current) return;

    const svg = d3.select(chartRef.current);
    svg.selectAll('*').remove();

    const margin = { top: 10, right: 10, bottom: 30, left: 50 };
    const width = 500 - margin.left - margin.right;
    const height = 200 - margin.top - margin.bottom;

    const g = svg
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Prepare data
    const bids = orderBook.bids.slice(0, 20);
    const asks = orderBook.asks.slice(0, 20);
    const allPrices = [...bids, ...asks];

    const xScale = d3
      .scaleLinear()
      .domain([
        d3.min(allPrices, (d) => d.price) || 0,
        d3.max(allPrices, (d) => d.price) || 0,
      ])
      .range([0, width]);

    const yScale = d3
      .scaleLinear()
      .domain([0, d3.max(allPrices, (d) => d.total) || 0])
      .range([height, 0]);

    // Draw bid area
    const bidArea = d3
      .area<typeof bids[0]>()
      .x((d) => xScale(d.price))
      .y0(height)
      .y1((d) => yScale(d.total))
      .curve(d3.curveStepAfter);

    g.append('path')
      .datum(bids)
      .attr('fill', 'rgba(34, 197, 94, 0.3)')
      .attr('stroke', 'rgb(34, 197, 94)')
      .attr('stroke-width', 2)
      .attr('d', bidArea);

    // Draw ask area
    const askArea = d3
      .area<typeof asks[0]>()
      .x((d) => xScale(d.price))
      .y0(height)
      .y1((d) => yScale(d.total))
      .curve(d3.curveStepAfter);

    g.append('path')
      .datum(asks)
      .attr('fill', 'rgba(239, 68, 68, 0.3)')
      .attr('stroke', 'rgb(239, 68, 68)')
      .attr('stroke-width', 2)
      .attr('d', askArea);

    // Draw mid price line
    g.append('line')
      .attr('x1', xScale(orderBook.mid_price))
      .attr('x2', xScale(orderBook.mid_price))
      .attr('y1', 0)
      .attr('y2', height)
      .attr('stroke', 'rgba(255, 255, 255, 0.5)')
      .attr('stroke-width', 1)
      .attr('stroke-dasharray', '4,4');

    // Axes
    g.append('g')
      .attr('transform', `translate(0,${height})`)
      .call(d3.axisBottom(xScale).ticks(5))
      .attr('color', 'rgba(255, 255, 255, 0.5)');

    g.append('g')
      .call(d3.axisLeft(yScale).ticks(5))
      .attr('color', 'rgba(255, 255, 255, 0.5)');
  }, [orderBook]);

  if (!orderBook) {
    return (
      <div className="orderbook">
        <h2>Order Book - {symbol}</h2>
        <div className="orderbook-loading">Loading...</div>
      </div>
    );
  }

  return (
    <div className="orderbook">
      <h2>Order Book - {symbol}</h2>

      <div className="orderbook-stats">
        <div className="stat">
          <span className="stat-label">Mid Price:</span>
          <span className="stat-value">${orderBook.mid_price.toFixed(2)}</span>
        </div>
        <div className="stat">
          <span className="stat-label">Spread:</span>
          <span className="stat-value">${orderBook.spread.toFixed(4)}</span>
        </div>
      </div>

      <div className="orderbook-chart">
        <svg ref={chartRef} width="500" height="200" />
      </div>

      <div className="orderbook-tables">
        <div className="orderbook-table bids">
          <h3>Bids</h3>
          <div className="table-header">
            <span>Price</span>
            <span>Size</span>
            <span>Total</span>
          </div>
          {orderBook.bids.slice(0, 10).map((bid, idx) => (
            <div key={idx} className="table-row">
              <span className="price">${bid.price.toFixed(2)}</span>
              <span className="size">{bid.quantity.toFixed(4)}</span>
              <span className="total">{bid.total.toFixed(4)}</span>
            </div>
          ))}
        </div>

        <div className="orderbook-table asks">
          <h3>Asks</h3>
          <div className="table-header">
            <span>Price</span>
            <span>Size</span>
            <span>Total</span>
          </div>
          {orderBook.asks.slice(0, 10).map((ask, idx) => (
            <div key={idx} className="table-row">
              <span className="price">${ask.price.toFixed(2)}</span>
              <span className="size">{ask.quantity.toFixed(4)}</span>
              <span className="total">{ask.total.toFixed(4)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
