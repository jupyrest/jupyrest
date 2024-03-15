import React, { useState } from 'react';
import axios from 'axios';

interface ApiResponse {
    input_schema: string;
}

export default function FormComponent() {
    const [notebookId, setNotebookId] = useState<string>('');
    const [inputSchema, setInputSchema] = useState<string>('');

    const handleSubmit = async (event: React.FormEvent) => {
        event.preventDefault();
        try {
            const response = await axios.get<ApiResponse>(`http://localhost:5050/api/NotebookExecutions?id=${notebookId}`);
            setInputSchema(response.data.input_schema);
        } catch (error) {
            console.error('Error fetching data:', error);
        }
    };

    return (
        <div>
            <form onSubmit={handleSubmit}>
                <label>
                    Notebook ID:
                    <input type="text" value={notebookId} onChange={(e) => setNotebookId(e.target.value)} />
                </label>
                <button type="submit">Submit</button>
            </form>

            {inputSchema && (
                <div>
                    <h2>Input Schema:</h2>
                    <p>{inputSchema}</p>
                </div>
            )}

            {/* Your custom form component MyForm can be rendered here */}
            {/* <MyForm inputSchema={inputSchema} /> */}
        </div>
    );
};
