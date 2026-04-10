import { NavLink } from "react-router-dom";

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="logo-wrap">
        <h2 className="logo">Lumina</h2>
        <p className="logo-subtitle">Operator Dashboard</p>
      </div>

      <nav className="nav-links">
        <NavLink to="/chat">Chat</NavLink>
        <NavLink to="/cluster">Cluster</NavLink>
        <NavLink to="/health">Health</NavLink>
        <NavLink to="/trace">Trace</NavLink>
      </nav>
    </aside>
  );
}