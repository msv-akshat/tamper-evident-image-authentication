import { useState } from "react";

function StepCard({ title, explain, active, children }) {
  const [open, setOpen] = useState(true);

  return (
    <article className={`step-card ${active ? "active" : ""}`}>
      <header className="step-header">
        <div>
          <h4>{title}</h4>
          <p>{explain}</p>
        </div>
        <div className="step-actions">
          <span className="tooltip-pill" title={explain}>
            Explain
          </span>
          <button className="mini-button" onClick={() => setOpen((prev) => !prev)}>
            {open ? "Collapse" : "Expand"}
          </button>
        </div>
      </header>
      {open && <div className="step-body">{children}</div>}
    </article>
  );
}

export default StepCard;
