import React from 'react';
import ReactDOM from 'react-dom/client';

// Leaflet'in zorunlu stilleri – global reset'ten ÖNCE yüklenmeli.
import 'leaflet/dist/leaflet.css';
import './styles/global.css';

import App from './App.jsx';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
