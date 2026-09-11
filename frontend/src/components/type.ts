export interface Experiment {
    id: string;
    name: string;
    numDay: number;
    status: number;
    curDay: number;
    curT: number;
    config: string;
    error: string;
    inputTokens: number;
    outputTokens: number;
    createdAt: string;
    updatedAt: string;
    num_day?: number;
    cur_day?: number;
    cur_t?: number;
    input_tokens?: number;
    output_tokens?: number;
    created_at?: string;
    updated_at?: string;
}

export const experimentStatusMap: { [key: number]: string } = {
    0: 'Not Started',
    1: 'Running',
    2: 'Completed',
    3: 'Error Interrupted'
};

export interface Survey {
    id: string;
    name: string;
    data: any;
    createdAt: string;
    updatedAt: string;
}
