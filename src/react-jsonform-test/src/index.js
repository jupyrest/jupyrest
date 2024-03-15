import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import { App2 } from "/home/koushik/code/jupyrest2/src/my-ts-react-app/src/App";
// import {FormComponent} from "/home/koushik/code/jupyrest2/src/my-ts-react-app/src/SchemaForm";
import reportWebVitals from './reportWebVitals';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App2 />
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
