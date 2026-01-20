import React, { useState, useMemo } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend, BarChart, Bar, XAxis, YAxis } from 'recharts';
import { Activity, TrendingUp, User, Database, Upload, ArrowUpDown, Zap, Wallet, CreditCard, RefreshCw, Clock, Target } from 'lucide-react';

// สีธีม
const PIE_COLORS = ['#00f2ff', '#7000ff', '#ff00c8', '#00ff41', '#ffea00', '#ff5e00'];

const App = () => {
  const [initialData, setInitialData] = useState([]);
  const [displayData, setDisplayData] = useState([]);
  const [fileName, setFileName] = useState("เลือกไฟล์ CSV");
  const [sortConfig, setSortConfig] = useState({ key: 'Weight_Percent', direction: 'desc' });
  const [lastUpdated, setLastUpdated] = useState(null);

  // --- CSV Parsing ---
  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setFileName(file.name);

    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target.result;
      const lines = text.trim().split('\n');
      const headers = lines[0].split(',').map(h => h.trim());
      const parsed = lines.slice(1).filter(l => l).map(line => {
        const values = line.split(',');
        return headers.reduce((obj, header, i) => {
          const val = values[i]?.trim();
          obj[header] = isNaN(val) ? val : parseFloat(val);
          return obj;
        }, {});
      });

      // Enrich Data
      const enriched = parsed.map(item => {
        let cat = item.Category ? item.Category.toUpperCase() : 'SATELLITE';
        if (!item.Category) {
           const sym = item.Symbol.toUpperCase();
           if (['VOO','V','SCHD','IVV','LLY'].includes(sym)) cat = 'CORE';
           if (['CASH','USD'].includes(sym)) cat = 'CASH';
        }
        
        const shares = parseFloat(item.Shares) || 0;
        const totalCost = parseFloat(item.Total_Cost_USD) || 0;
        const currentPrice = parseFloat(item.Current_Price_USD) || 0;
        const marketValue = shares * currentPrice;

        return {
          ...item,
          Category: cat,
          Shares: shares,
          Current_Price_USD: currentPrice,
          Cost_Per_Share_USD: shares > 0 ? totalCost / shares : 0,
          Total_Cost_USD: totalCost,
          Asset_Value_USD: marketValue,
          Gain_USD: marketValue - totalCost,
          Gain_Percent: totalCost > 0 ? ((marketValue - totalCost) / totalCost) * 100 : 0,
          
          // Technical Data
          Target_Price: parseFloat(item.Target_Price) || 0,
          Support_S1: parseFloat(item.Support_S1) || 0,
          RSI: parseFloat(item.RSI) || 50,
          EMA50: parseFloat(item.EMA50) || 0,
          EMA200: parseFloat(item.EMA200) || 0
        };
      });

      setInitialData(enriched);
      setDisplayData(enriched);
      setLastUpdated(new Date());
    };
    reader.readAsText(file);
  };

  // --- Manual Refresh ---
  const refreshMarketData = () => {
    if (initialData.length === 0) return;
    const updated = initialData.map(item => {
      if (item.Category === 'CASH') return item;
      const change = (Math.random() - 0.5) * 0.02; 
      const newPrice = item.Current_Price_USD * (1 + change);
      const newMarketValue = item.Shares * newPrice;
      const newGainUSD = newMarketValue - item.Total_Cost_USD;
      return {
        ...item,
        Current_Price_USD: newPrice,
        Asset_Value_USD: newMarketValue,
        Gain_USD: newGainUSD,
        Gain_Percent: item.Total_Cost_USD > 0 ? (newGainUSD / item.Total_Cost_USD) * 100 : 0
      };
    });
    setDisplayData(updated);
    setLastUpdated(new Date());
  };

  // --- Sorting ---
  const sortedData = useMemo(() => {
    let items = [...displayData];
    if (sortConfig.key) {
      items.sort((a, b) => {
        if (a[sortConfig.key] < b[sortConfig.key]) return sortConfig.direction === 'asc' ? -1 : 1;
        if (a[sortConfig.key] > b[sortConfig.key]) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
      });
    }
    return items;
  }, [displayData, sortConfig]);

  const requestSort = (key) => {
    setSortConfig(prev => ({ 
      key, 
      direction: prev.key === key && prev.direction === 'desc' ? 'asc' : 'desc' 
    }));
  };

  // --- Stats ---
  const stats = useMemo(() => {
    if (displayData.length === 0) return { totalValue: 0, totalGain: 0, gainPercent: 0, cash: 0, coreWeight: 0, satWeight: 0 };
    const totalVal = displayData.reduce((acc, curr) => acc + (curr.Asset_Value_USD || 0), 0);
    const totalCost = displayData.reduce((acc, curr) => acc + (curr.Total_Cost_USD || 0), 0);
    const totalG = totalVal - totalCost;

    const cashObj = displayData.find(d => d.Category === 'CASH');
    const cashVal = cashObj ? cashObj.Asset_Value_USD : 0;
    const investableValue = totalVal - cashVal;
    
    const coreVal = displayData.filter(d => d.Category === 'CORE').reduce((acc, curr) => acc + curr.Asset_Value_USD, 0);
    const satVal = displayData.filter(d => d.Category === 'SATELLITE').reduce((acc, curr) => acc + curr.Asset_Value_USD, 0);

    return {
      totalValue: totalVal,
      totalGain: totalG,
      gainPercent: totalCost > 0 ? (totalG / totalCost) * 100 : 0,
      cash: cashVal,
      coreWeight: investableValue > 0 ? (coreVal / investableValue) * 100 : 0,
      satWeight: investableValue > 0 ? (satVal / investableValue) * 100 : 0
    };
  }, [displayData]);

  return (
    <div className="min-h-screen bg-[#05050a] text-gray-100 font-sans p-6 lg:p-10 selection:bg-cyan-500/30">
      <div className="fixed inset-0 pointer-events-none -z-10">
        <div className="absolute top-[-20%] right-[-10%] w-[1000px] h-[1000px] bg-cyan-500/5 blur-[180px] rounded-full mix-blend-screen"></div>
        <div className="absolute bottom-[-20%] left-[-10%] w-[1000px] h-[1000px] bg-purple-600/5 blur-[180px] rounded-full mix-blend-screen"></div>
      </div>

      <div className="max-w-[2000px] mx-auto space-y-8">
        
        {/* HEADER */}
        <header className="bg-[#11111e]/90 border border-white/10 rounded-[2rem] p-8 shadow-2xl backdrop-blur-xl">
           <div className="flex flex-col xl:flex-row justify-between items-center gap-8">
              <div className="flex items-center gap-8 min-w-[300px]">
                <div className="p-5 bg-gradient-to-br from-cyan-500/20 to-blue-600/20 rounded-3xl border border-cyan-400/40">
                  <User size={48} className="text-cyan-400" />
                </div>
                <div>
                  <h1 className="text-3xl lg:text-4xl font-black text-white mb-2">GOLF'S TERMINAL</h1>
                  <div className="flex items-center gap-3 text-gray-400 text-sm">
                    <Clock size={16} />
                    <p className="font-mono tracking-widest uppercase">
                      Updated: {lastUpdated ? lastUpdated.toLocaleTimeString() : '--:--:--'}
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex gap-4">
                 <button onClick={refreshMarketData} className="flex items-center gap-2 bg-cyan-500/10 hover:bg-cyan-500 hover:text-white border border-cyan-500/40 text-cyan-400 px-6 py-4 rounded-xl transition-all group">
                    <RefreshCw size={24} className="group-hover:rotate-180 transition-transform duration-500" />
                    <span className="font-bold uppercase tracking-wider text-sm">Refresh</span>
                 </button>
                 <label className="flex items-center gap-4 bg-white/5 hover:bg-white/10 border border-white/10 px-8 py-4 rounded-xl cursor-pointer transition-all group">
                    <Upload size={24} className="text-gray-400 group-hover:text-white" />
                    <div><span className="block text-xs text-gray-500 uppercase">Source</span><span className="block text-base font-bold text-white">{fileName}</span></div>
                    <input type="file" accept=".csv" onChange={handleFileUpload} className="hidden" />
                 </label>
              </div>
           </div>

           {/* METRICS */}
           <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mt-10 border-t border-white/5 pt-10">
              <div className="relative">
                 <div className="flex items-center gap-3 mb-2 text-gray-400"><Wallet size={24} /><span className="text-sm font-bold uppercase tracking-widest">Equity</span></div>
                 <div className="text-7xl font-black text-white tracking-tighter">${stats.totalValue.toLocaleString(undefined, {maximumFractionDigits: 0})}</div>
              </div>
              <div className="relative border-l border-white/10 pl-8">
                 <div className="flex items-center gap-3 mb-2 text-gray-400"><TrendingUp size={24} /><span className="text-sm font-bold uppercase tracking-widest">P/L</span></div>
                 <div className={`text-7xl font-black tracking-tighter ${stats.totalGain >= 0 ? 'text-[#10b981]' : 'text-[#ef4444]'}`}>
                    {stats.totalGain >= 0 ? '+' : ''}{stats.gainPercent.toFixed(2)}%
                 </div>
              </div>
              <div className="relative border-l border-white/10 pl-8">
                 <div className="flex items-center gap-3 mb-2 text-gray-400"><CreditCard size={24} /><span className="text-sm font-bold uppercase tracking-widest">Cash</span></div>
                 <div className="text-6xl font-black text-white tracking-tighter">${stats.cash.toLocaleString()}</div>
                 <div className="mt-4 flex gap-1 h-3 w-full bg-white/10 rounded-full overflow-hidden">
                    <div className="bg-cyan-500" style={{ width: `${stats.coreWeight}%` }}></div>
                    <div className="bg-purple-500" style={{ width: `${stats.satWeight}%` }}></div>
                 </div>
              </div>
           </div>
        </header>

        {/* CONTENT */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          <div className="lg:col-span-3 space-y-8">
             <div className="bg-[#11111e] border border-white/5 rounded-[2rem] p-8 h-[400px]">
                <h2 className="text-base font-bold text-gray-400 uppercase tracking-widest mb-6 flex gap-3"><Activity size={20} className="text-cyan-400"/> Allocation</h2>
                <ResponsiveContainer width="100%" height="85%">
                  <PieChart>
                    <Pie data={displayData.filter(d => d.Category !== 'CASH')} dataKey="Asset_Value_USD" nameKey="Symbol" cx="50%" cy="50%" innerRadius={70} outerRadius={100} paddingAngle={4} stroke="none">
                      {displayData.filter(d => d.Category !== 'CASH').map((entry, index) => <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />)}
                    </Pie>
                    <Tooltip contentStyle={{ backgroundColor: '#05050a', border: '1px solid #333' }} />
                    <Legend verticalAlign="bottom" wrapperStyle={{fontSize:'12px'}}/>
                  </PieChart>
                </ResponsiveContainer>
             </div>
             
             <div className="bg-[#11111e] border border-white/5 rounded-[2rem] p-8 h-[400px]">
                <h2 className="text-base font-bold text-gray-400 uppercase tracking-widest mb-6 flex gap-3"><Zap size={20} className="text-purple-400"/> Gainers</h2>
                <ResponsiveContainer width="100%" height="85%">
                  <BarChart data={[...displayData].filter(d=>d.Category!=='CASH').sort((a,b) => b.Gain_Percent - a.Gain_Percent).slice(0,5)} layout="vertical" margin={{ left: 5 }}>
                    <XAxis type="number" hide />
                    <YAxis dataKey="Symbol" type="category" width={50} tick={{fill: '#fff', fontSize: 14, fontWeight: 'bold'}} axisLine={false} tickLine={false} />
                    <Bar dataKey="Gain_Percent" fill="#00f2ff" radius={[0, 6, 6, 0]} barSize={24}>
                      {displayData.filter(d=>d.Category!=='CASH').map((entry, index) => <Cell key={`bar-${index}`} fill={entry.Gain_Percent >= 0 ? '#10b981' : '#ef4444'} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
             </div>
          </div>

          {/* TABLE - TECHNICAL ANALYSIS */}
          <div className="lg:col-span-9 bg-[#11111e] border border-white/5 rounded-[2rem] p-8 flex flex-col">
             <div className="flex justify-between items-center mb-8">
               <h2 className="text-2xl font-bold text-white uppercase tracking-widest flex gap-3">
                  <Database size={28} className="text-gray-500"/> Tactical Inventory
               </h2>
               <div className="flex gap-4 text-xs uppercase font-bold text-gray-500">
                  <span className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-green-500"></span> BUY/DISCOUNT</span>
                  <span className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-cyan-400"></span> BULL/UPTREND</span>
               </div>
             </div>
             
             <div className="overflow-x-auto">
               <table className="w-full text-left border-collapse">
                 <thead className="text-sm uppercase tracking-widest text-gray-500 border-b-2 border-white/10">
                   <tr>
                     <th className="pb-6 pl-4 cursor-pointer hover:text-white" onClick={() => requestSort('Symbol')}>Asset <ArrowUpDown size={12} className="inline opacity-50"/></th>
                     <th className="pb-6 text-right">Price</th>
                     <th className="pb-6 text-center">RSI (14)</th>
                     <th className="pb-6 text-center">Trend Signals (EMA)</th>
                     <th className="pb-6 text-right">Diff S1 (%)</th>
                     <th className="pb-6 text-right">Upside %</th>
                     <th className="pb-6 text-center">PNL</th>
                   </tr>
                 </thead>
                 <tbody className="divide-y divide-white/5 font-mono text-base">
                   {sortedData.map((asset, idx) => {
                      if (asset.Category === 'CASH') return null;
                      const isProfit = asset.Gain_Percent >= 0;
                      
                      const upside = asset.Target_Price > 0 ? ((asset.Target_Price - asset.Current_Price_USD) / asset.Current_Price_USD) * 100 : 0;
                      const diffS1 = asset.Support_S1 > 0 ? ((asset.Current_Price_USD - asset.Support_S1) / asset.Support_S1) * 100 : 0;
                      
                      const isRsiBuy = asset.RSI <= 30;
                      const isRsiSell = asset.RSI >= 70;

                      // EMA Logic: โชว์ทุกสถานะ
                      const statusEMA50 = asset.EMA50 > 0 ? (asset.Current_Price_USD > asset.EMA50 ? "BULL" : "DISCOUNT") : "N/A";
                      const statusEMA200 = asset.EMA200 > 0 ? (asset.Current_Price_USD > asset.EMA200 ? "BULL" : "DISCOUNT") : "N/A";

                      return (
                        <tr key={idx} className="hover:bg-white/5 transition-colors group text-lg">
                          <td className="py-6 pl-4">
                            <div className="flex items-center gap-4">
                               <div className={`w-1.5 h-10 rounded-full ${asset.Category === 'CORE' ? 'bg-cyan-500' : 'bg-purple-500'}`}></div>
                               <div>
                                 <span className="block font-black text-white text-xl">{asset.Symbol}</span>
                                 <span className="block text-xs font-bold text-gray-500 uppercase">{asset.Category}</span>
                               </div>
                            </div>
                          </td>
                          <td className="py-6 text-right font-bold text-white text-xl">
                             ${(asset.Current_Price_USD || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                          </td>
                          
                          {/* RSI */}
                          <td className="py-6 text-center">
                             <span className={`px-3 py-1 rounded-lg font-bold text-sm ${isRsiBuy ? 'bg-green-500 text-black shadow-[0_0_10px_#22c55e]' : isRsiSell ? 'bg-red-500 text-white' : 'text-gray-400 bg-white/5'}`}>
                                {asset.RSI.toFixed(0)}
                             </span>
                          </td>

                          {/* Trend Signals (Show Always) */}
                          <td className="py-6 text-center">
                             <div className="flex flex-col gap-2 items-center">
                                {/* EMA 50 */}
                                {statusEMA50 !== "N/A" && (
                                   <div className={`flex justify-between w-24 px-2 py-0.5 rounded text-xs font-bold border ${statusEMA50 === 'BULL' ? 'border-cyan-500/30 bg-cyan-500/10 text-cyan-400' : 'border-yellow-500/30 bg-yellow-500/10 text-yellow-400'}`}>
                                      <span>EMA50</span>
                                      <span>{statusEMA50}</span>
                                   </div>
                                )}
                                {/* EMA 200 */}
                                {statusEMA200 !== "N/A" && (
                                   <div className={`flex justify-between w-24 px-2 py-0.5 rounded text-xs font-bold border ${statusEMA200 === 'BULL' ? 'border-blue-500/30 bg-blue-500/10 text-blue-400' : 'border-green-500/30 bg-green-500/10 text-green-400'}`}>
                                      <span>EMA200</span>
                                      <span>{statusEMA200}</span>
                                   </div>
                                )}
                             </div>
                          </td>

                          {/* Diff S1 */}
                          <td className="py-6 text-right">
                             <span className={`font-bold ${diffS1 < 5 ? 'text-yellow-400' : 'text-gray-400'}`}>
                                {diffS1.toFixed(2)}%
                             </span>
                             <div className="text-xs text-gray-600">from ${asset.Support_S1}</div>
                          </td>

                          {/* Upside % */}
                          <td className="py-6 text-right">
                             <div className="flex items-center justify-end gap-2">
                                <Target size={16} className="text-cyan-500/50" />
                                <span className="font-bold text-cyan-400 text-lg">+{upside.toFixed(1)}%</span>
                             </div>
                             <div className="text-xs text-gray-600">TP: ${asset.Target_Price}</div>
                          </td>

                          {/* PNL */}
                          <td className="py-6 px-4 text-center">
                              <span className={`block font-black text-lg ${isProfit ? 'text-green-400' : 'text-red-400'}`}>
                                {isProfit ? '+' : ''}{asset.Gain_Percent?.toFixed(2)}%
                              </span>
                              <span className="text-xs text-gray-500 font-bold">${Math.abs(asset.Gain_USD).toFixed(0)}</span>
                          </td>
                        </tr>
                      );
                   })}
                 </tbody>
               </table>
             </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;
