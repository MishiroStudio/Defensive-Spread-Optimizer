import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { registerSW } from "virtual:pwa-register";

import PokedexApp from "./pokedex-app";
import "./pokedex.css";

registerSW({ immediate: true });

const root = document.getElementById("root");
if (!root) throw new Error("Root element not found.");

createRoot(root).render(
  <StrictMode>
    <PokedexApp />
  </StrictMode>,
);
