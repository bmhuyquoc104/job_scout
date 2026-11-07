import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { loadSources } from "./api/client";
import App from "./App";

// The job-source list comes from the backend; if it can't be loaded the app still renders (ids as names).
loadSources()
  .catch(() => undefined)
  .then(() =>
    ReactDOM.createRoot(document.getElementById("root")!).render(
      <React.StrictMode>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </React.StrictMode>,
    ),
  );
