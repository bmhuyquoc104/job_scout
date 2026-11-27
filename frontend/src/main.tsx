import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { loadSources } from "./api/client";
import App from "./App";

const root = ReactDOM.createRoot(document.getElementById("root")!);
const show = (key: number) =>
  root.render(
    <React.StrictMode>
      <BrowserRouter key={key}>
        <App />
      </BrowserRouter>
    </React.StrictMode>,
  );

// Render at once: the host may be asleep, and the first API call can take a minute. The job-source
// names arrive later and the app is shown again with them; if they can't be loaded, ids are shown.
// shortcut: the second render remounts the app (state resets), fine since it lands before any input.
show(0);
loadSources()
  .then(() => show(1))
  .catch(() => undefined);
