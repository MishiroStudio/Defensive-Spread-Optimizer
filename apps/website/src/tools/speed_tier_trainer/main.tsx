// main.tsx — Speed Tier Trainer PWA V1
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { registerSW } from "virtual:pwa-register";

import SpeedTierTrainerApp from "./speed-tier-trainer-app";
import "./speed-tier-trainer.css";

registerSW({ immediate: true });

const root = document.getElementById("root");
if (!root) throw new Error("Root element not found.");

createRoot(root).render(
  <StrictMode>
    <SpeedTierTrainerApp />
  </StrictMode>,
);
