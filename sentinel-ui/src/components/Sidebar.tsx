"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  LayoutDashboard, 
  ShieldAlert, 
  Settings2, 
  Eye, 
  CheckSquare, 
  Users, 
  FileText,
  LogOut 
} from "lucide-react";

export function Sidebar() {
  const pathname = usePathname();

  const navItems = [
    { name: "Dashboard", href: "/", icon: LayoutDashboard },
    { name: "Alerted Entities", href: "/alerts", icon: ShieldAlert },
    { name: "Logic Management", href: "/logic", icon: Settings2 },
    { name: "Watchlist Management", href: "/watchlist", icon: Eye },
    { name: "Workflow Approval", href: "/workflow", icon: CheckSquare },
    { name: "User Management", href: "/users", icon: Users },
    { name: "Audit Log", href: "/audit", icon: FileText },
  ];

  return (
    <div className="w-64 h-screen border-r bg-white flex flex-col fixed left-0 top-0">
      <div className="p-6 border-b flex items-center gap-2">
        <ShieldAlert className="h-6 w-6 text-slate-800" />
        <span className="font-bold text-lg tracking-tight">NxGraph</span>
        <span className="text-[10px] text-slate-500 font-semibold uppercase mt-1">Fraud Analytics</span>
      </div>
      
      <div className="flex-1 py-6 px-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
                isActive 
                  ? "bg-blue-50 text-blue-600" 
                  : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
              }`}
            >
              <item.icon className={`h-4 w-4 ${isActive ? "text-blue-600" : "text-slate-400"}`} />
              {item.name}
            </Link>
          );
        })}
      </div>

      <div className="p-4 border-t">
        <button className="flex items-center gap-3 px-4 py-3 w-full text-sm font-medium text-slate-600 hover:bg-slate-50 hover:text-rose-600 rounded-lg transition-colors">
          <LogOut className="h-4 w-4 text-slate-400" />
          Logout
        </button>
      </div>
    </div>
  );
}
