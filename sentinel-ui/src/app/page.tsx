"use client";

import { useState, useEffect } from "react";
import { UserCircle, Calendar, ChevronDown, BellRing, Repeat, Target, Wallet } from "lucide-react";
import { io } from "socket.io-client";

export default function Dashboard() {
  const [stats, setStats] = useState({
    alerts: 75,
    entities: 84,
    transactions: 85,
    amount: "Rp 1.25 Bn",
  });

  const [recentAlerts, setRecentAlerts] = useState<any[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    // Attempt WebSocket Connection
    const socket = io("http://localhost:5000");

    socket.on("connect", () => setIsConnected(true));
    socket.on("disconnect", () => setIsConnected(false));

    socket.on("new_alert", (data) => {
      // Append new real-time alerts from engine
      setRecentAlerts((prev) => [data, ...prev].slice(0, 10));
    });

    return () => {
      socket.disconnect();
    };
  }, []);

  return (
    <div className="flex-1 p-8 bg-slate-50 min-h-screen">
      {/* Top Header */}
      <header className="flex justify-between items-center mb-8">
        <div className="flex items-center gap-2 text-sm text-slate-500">
          <span>Home</span>
          <span>/</span>
          <span className="font-semibold text-slate-900">Dashboard</span>
        </div>

        <div className="flex gap-4 items-center">
          <div className={`px-3 py-1 text-xs rounded-full font-bold ${isConnected ? "bg-emerald-100 text-emerald-700" : "bg-rose-100 text-rose-700"}`}>
            {isConnected ? "Engine Connected" : "Connecting..."}
          </div>
          <div className="flex items-center gap-3 bg-white px-4 py-2 flex-shrink-0 cursor-pointer rounded-full shadow-sm border hover:bg-slate-50 transition">
            <UserCircle className="h-5 w-5 text-slate-600" />
            <span className="text-sm font-medium text-slate-700">superadmin@nxfraud.com</span>
          </div>
        </div>
      </header>

      {/* Main Title */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Dashboard</h1>
        <p className="text-slate-500">Real-time fraud detection insights and analytics</p>
      </div>

      {/* Filters */}
      <div className="flex gap-6 mb-8 items-center bg-white p-4 rounded-xl shadow-sm border">
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold text-slate-700">Category:</span>
          <div className="flex items-center justify-between border rounded-lg px-4 py-2 w-64 bg-slate-50 cursor-pointer">
            <span className="text-sm text-slate-600">All Categories</span>
            <ChevronDown className="h-4 w-4 text-slate-400" />
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold text-slate-700">Date Range:</span>
          <div className="flex items-center gap-3 border rounded-lg px-4 py-2 bg-slate-50 cursor-pointer">
            <span className="text-sm text-slate-600">2026-02-18 &rarr; 2026-03-18</span>
            <Calendar className="h-4 w-4 text-slate-400" />
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-4 gap-6 mb-8">
        {/* Card 1 */}
        <div className="bg-white p-6 rounded-xl shadow-sm border flex flex-col justify-between">
          <p className="text-sm font-medium text-slate-500 mb-4">Total Alerts</p>
          <div className="flex items-center gap-4">
            <div className="bg-rose-50 p-3 rounded-lg">
              <BellRing className="h-8 w-8 text-rose-500" />
            </div>
            <div>
              <h2 className="text-3xl font-bold text-slate-900">{stats.alerts + recentAlerts.length}</h2>
              <p className="text-xs text-rose-500 font-medium mt-1">↘ 0.8% vs last period</p>
            </div>
          </div>
        </div>

        {/* Card 2 */}
        <div className="bg-white p-6 rounded-xl shadow-sm border flex flex-col justify-between">
          <p className="text-sm font-medium text-slate-500 mb-4">Total Alerted Entities</p>
          <div className="flex items-center gap-4">
            <div className="bg-blue-50 p-3 rounded-lg">
              <Target className="h-8 w-8 text-slate-400" />
            </div>
            <div>
              <h2 className="text-3xl font-bold text-slate-900">{stats.entities}</h2>
              <p className="text-xs text-rose-500 font-medium mt-1">↘ 0.3% vs last period</p>
            </div>
          </div>
        </div>

        {/* Card 3 */}
        <div className="bg-white p-6 rounded-xl shadow-sm border flex flex-col justify-between">
          <p className="text-sm font-medium text-slate-500 mb-4">Total Alerted Transactions</p>
          <div className="flex items-center gap-4">
            <div className="bg-amber-50 p-3 rounded-lg">
              <Repeat className="h-8 w-8 text-amber-500" />
            </div>
            <div>
              <h2 className="text-3xl font-bold text-slate-900">{stats.transactions}</h2>
              <p className="text-xs text-rose-500 font-medium mt-1">↘ 0.7% vs last period</p>
            </div>
          </div>
        </div>

        {/* Card 4 */}
        <div className="bg-white p-6 rounded-xl shadow-sm border flex flex-col justify-between">
          <p className="text-sm font-medium text-slate-500 mb-4">Total Alerted Amount</p>
          <div className="flex items-center gap-4">
            <div className="bg-slate-50 p-3 rounded-lg">
              <Wallet className="h-8 w-8 text-slate-400" />
            </div>
            <div>
              <h2 className="text-3xl font-bold text-slate-900">{stats.amount}</h2>
              <p className="text-xs text-rose-500 font-medium mt-1">↘ 0.9% vs last period</p>
            </div>
          </div>
        </div>
      </div>

      {/* Real-time Alerts Panel */}
      <div className="bg-white border rounded-xl shadow-sm p-6 min-h-[400px]">
        <div className="flex justify-between items-center mb-6">
          <h3 className="font-semibold text-slate-900">Live Rule Breaches</h3>
          <span className="text-xs text-slate-500 flex items-center gap-2">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-rose-500"></span>
            </span>
            Listening to Flask Engine...
          </span>
        </div>

        {recentAlerts.length === 0 ? (
          <div className="text-center py-10 text-slate-400 text-sm">Waiting for incoming anomalies...</div>
        ) : (
          <div className="space-y-3">
            {recentAlerts.map((alert, idx) => (
              <div key={idx} className="w-full bg-rose-50 border border-rose-100 p-4 rounded-lg text-rose-900 flex justify-between cursor-pointer hover:bg-rose-100 transition">
                <div>
                  <span className="font-bold text-sm block">{alert.type}</span>
                  <span className="text-xs text-rose-700">{alert.desc}</span>
                </div>
                <div className="text-right">
                  <span className="font-mono text-xs block text-slate-500">{alert.tx_id}</span>
                  <span className="font-bold text-rose-600 bg-white px-2 py-1 rounded text-xs">Score: {alert.score}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Fixed history for showcase */}
        <div className="w-full mt-6 bg-blue-500 p-4 rounded text-white flex justify-between cursor-pointer hover:bg-blue-600 transition">
          <span className="font-medium text-sm">Repeated Small Transactions to One Account</span>
          <span className="font-bold">39</span>
        </div>
        <div className="w-full mt-2 bg-slate-100 border p-4 rounded text-slate-700 flex justify-between cursor-pointer hover:bg-slate-200 transition">
          <span className="font-medium text-sm">Time and Value Anomaly</span>
          <span className="font-bold">12</span>
        </div>
        <div className="w-full mt-2 bg-slate-100 border p-4 rounded text-slate-700 flex justify-between cursor-pointer hover:bg-slate-200 transition">
          <span className="font-medium text-sm">Merchant Cashback Abuse</span>
          <span className="font-bold">8</span>
        </div>
      </div>

    </div>
  );
}
