// Lokalny model językowy (WebLLM) w osobnym wątku - liczy na karcie graficznej telefonu przez WebGPU.
import { WebWorkerMLCEngineHandler } from "https://cdn.jsdelivr.net/npm/@mlc-ai/web-llm@0.2.85/+esm";

const obsluga = new WebWorkerMLCEngineHandler();
self.onmessage = (wiadomosc) => obsluga.onmessage(wiadomosc);
