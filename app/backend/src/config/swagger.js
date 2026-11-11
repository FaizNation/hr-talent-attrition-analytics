export const swaggerDocument = {
  openapi: '3.0.0',
  info: {
    title: 'HR MNC Analytics & NoSQL Serving Layer API',
    version: '1.0.0',
    description:
      'Express.js REST API querying MongoDB 8.2 (db_hr_mnc) storing 2,000,000 employee records and analytical summaries.',
    contact: {
      name: 'Big Data HR Analytics Project',
    },
  },
  servers: [
    {
      url: 'http://localhost:5001',
      description: 'Local Development Server',
    },
  ],
  tags: [
    { name: 'System', description: 'Server health and status' },
    { name: 'Summaries', description: 'Pre-computed NoSQL macro summaries' },
    { name: 'Employees', description: '2,000,000 raw employee records & indexed lookups' },
  ],
  paths: {
    '/health': {
      get: {
        tags: ['System'],
        summary: 'Server Health Check',
        responses: {
          200: {
            description: 'Server is running normally',
            content: {
              'application/json': {
                schema: {
                  type: 'object',
                  properties: {
                    status: { type: 'string', example: 'ok' },
                    server_time: { type: 'string', example: '2026-11-11T13:00:00.000Z' },
                  },
                },
              },
            },
          },
        },
      },
    },
    '/api/overview': {
      get: {
        tags: ['Summaries'],
        summary: 'Global Organization Macro Summary',
        description: 'Returns macro metrics across all 2,000,000 employee records.',
        responses: {
          200: {
            description: 'Macro summary metrics',
            content: {
              'application/json': {
                schema: {
                  type: 'object',
                  properties: {
                    total_employees: { type: 'integer', example: 2000000 },
                    total_payroll_inr: { type: 'number', example: 3662580000000 },
                    avg_salary_inr: { type: 'number', example: 1831290.0 },
                    min_salary_inr: { type: 'integer', example: 300000 },
                    max_salary_inr: { type: 'integer', example: 2999976 },
                    avg_experience_years: { type: 'number', example: 7.5 },
                    avg_performance_rating: { type: 'number', example: 3.0 },
                    status_distribution: {
                      type: 'object',
                      example: { Active: 1400000, Resigned: 400000, 'On Leave': 100000, Terminated: 100000 },
                    },
                    work_mode_distribution: {
                      type: 'object',
                      example: { 'On-site': 1000500, Remote: 999500 },
                    },
                  },
                },
              },
            },
          },
        },
      },
    },
    '/api/departments': {
      get: {
        tags: ['Summaries'],
        summary: 'Department Summaries (7 Divisions)',
        description: 'Returns headcount and payroll statistics for all 7 departments.',
        responses: {
          200: {
            description: 'List of 7 department summaries',
            content: {
              'application/json': {
                schema: {
                  type: 'array',
                  items: {
                    type: 'object',
                    properties: {
                      _id: { type: 'string', example: 'IT' },
                      department: { type: 'string', example: 'IT' },
                      employee_count: { type: 'integer', example: 601042 },
                      headcount_percentage: { type: 'number', example: 30.05 },
                      total_payroll_inr: { type: 'number', example: 679093000000 },
                      avg_salary_inr: { type: 'number', example: 1129858.15 },
                      min_salary_inr: { type: 'integer', example: 300000 },
                      max_salary_inr: { type: 'integer', example: 2999976 },
                    },
                  },
                },
              },
            },
          },
        },
      },
    },
    '/api/job-titles': {
      get: {
        tags: ['Summaries'],
        summary: 'Job Title Salary Benchmarks (29 Roles)',
        description: 'Returns salary bounds and average experience for all 29 job titles.',
        responses: {
          200: {
            description: 'List of 29 job title summaries',
          },
        },
      },
    },
    '/api/work-modes': {
      get: {
        tags: ['Summaries'],
        summary: 'Work Mode Comparison (On-site vs Remote)',
        responses: {
          200: {
            description: 'Work mode breakdown',
          },
        },
      },
    },
    '/api/employees/{id}': {
      get: {
        tags: ['Employees'],
        summary: 'Single Employee O(1) Indexed Lookup',
        description:
          'Fast indexed lookup by Employee ID (e.g. EMP0000001 to EMP2000000) or numeric row_id across 2,000,000 documents.',
        parameters: [
          {
            name: 'id',
            in: 'path',
            required: true,
            description: 'Employee ID (e.g. EMP1000000) or row_id (e.g. 1000000)',
            schema: { type: 'string', example: 'EMP1000000' },
          },
        ],
        responses: {
          200: {
            description: 'Employee details found with query latency',
            content: {
              'application/json': {
                schema: {
                  type: 'object',
                  properties: {
                    _id: { type: 'string', example: 'EMP1000000' },
                    employee_id: { type: 'string', example: 'EMP1000000' },
                    row_id: { type: 'integer', example: 999999 },
                    full_name: { type: 'string', example: 'Nicholas Burton' },
                    department: { type: 'string', example: 'Operations' },
                    job_title: { type: 'string', example: 'Operations Executive' },
                    salary_inr: { type: 'integer', example: 1082735 },
                    performance_rating: { type: 'integer', example: 3 },
                    experience_years: { type: 'integer', example: 7 },
                    status: { type: 'string', example: 'Active' },
                    work_mode: { type: 'string', example: 'On-site' },
                    latency_ms: { type: 'number', example: 2.5 },
                  },
                },
              },
            },
          },
          404: {
            description: 'Employee not found',
            content: {
              'application/json': {
                schema: {
                  type: 'object',
                  properties: {
                    error: { type: 'string', example: "Employee with ID 'EMP9999999' not found" },
                    latency_ms: { type: 'number', example: 1.2 },
                  },
                },
              },
            },
          },
        },
      },
    },
    '/api/employees': {
      get: {
        tags: ['Employees'],
        summary: 'Paginated Employee Search & Filter',
        description: 'Browse employees with pagination and optional filters.',
        parameters: [
          { name: 'page', in: 'query', schema: { type: 'integer', default: 1 } },
          { name: 'limit', in: 'query', schema: { type: 'integer', default: 20 } },
          { name: 'department', in: 'query', schema: { type: 'string' } },
          { name: 'status', in: 'query', schema: { type: 'string' } },
          { name: 'work_mode', in: 'query', schema: { type: 'string' } },
        ],
        responses: {
          200: {
            description: 'Paginated employee list',
          },
        },
      },
    },
  },
};
