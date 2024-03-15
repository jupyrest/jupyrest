import React from 'react';
import logo from './logo.svg';
import './App.css';
// import Form from '@rjsf/core';
import Form from '@rjsf/bootstrap-4';
import { RJSFSchema } from '@rjsf/utils';
import validator from '@rjsf/validator-ajv8';
import ReactDOM from 'react-dom/client';


const notebookPicker: RJSFSchema = {
  "type": "object",
  "properties": {
    "notebook": {
      "type": "string"
    }
  },
  "required": [
    "notebook"
  ]
}

const schema: RJSFSchema = {
  "type": "object",
  "properties": {
    "incidents": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/incident"
      }
    },
    "foo": {
      "type": "string"
    }
  },
  "required": [
    "incidents",
    "foo"
  ],
  "definitions": {
    "incident": {
      "title": "Incident",
      "type": "object",
      "properties": {
        "start_time": {
          "title": "Start Time",
          "type": "string",
          "format": "date-time"
        },
        "end_time": {
          "title": "End Time",
          "type": "string",
          "format": "date-time"
        },
        "title": {
          "title": "Title",
          "type": "string"
        }
      },
      "required": [
        "start_time",
        "end_time",
        "title"
      ]
    }
  }
};

const log = (type: any) => console.log.bind(console, type);

export function App() {
  return (
    <div>

    <Form
      schema={schema}
      validator={validator}
      onChange={log('changed')}
      onSubmit={log('submitted')}
      onError={log('errors')}
    />
    </div>
  );
}


export default function App2() {
  const [formData, setFormData] = React.useState(null);

  function handleOnSubmit(e: any) {
    console.log(e.formData.notebook)
  }
  return (
    <>
    <Form
      schema={notebookPicker}
      validator={validator}
      onChange={log('changed1')}
      onSubmit={handleOnSubmit}
      onError={handleOnSubmit} />

      <Form
        schema={schema}
        validator={validator}
        onChange={log('changed')}
        onSubmit={log('submitted')}
        onError={log('errors')} />
    </>
  );
}
