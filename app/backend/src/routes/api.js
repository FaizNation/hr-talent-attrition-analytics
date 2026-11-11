import express from 'express';
import { getDB } from '../config/db.js';

const router = express.Router();

// 1. Overview summary
router.get('/overview', async (req, res) => {
  try {
    const db = getDB();
    const overview = await db.collection('hr_overview_summary').findOne({ _id: 'global' });
    if (!overview) {
      return res.status(404).json({ error: 'Overview summary not found' });
    }
    res.json(overview);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 2. Department summary (7 docs)
router.get('/departments', async (req, res) => {
  try {
    const db = getDB();
    const departments = await db.collection('department_summary').find().sort({ employee_count: -1 }).toArray();
    res.json(departments);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 3. Job title summary (29 docs)
router.get('/job-titles', async (req, res) => {
  try {
    const db = getDB();
    const jobTitles = await db.collection('job_title_summary').find().sort({ employee_count: -1 }).toArray();
    res.json(jobTitles);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 4. Work mode summary (2 docs)
router.get('/work-modes', async (req, res) => {
  try {
    const db = getDB();
    const workModes = await db.collection('work_mode_summary').find().toArray();
    res.json(workModes);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 5. Single Employee Lookup by ID (O(1) indexed query over 2,000,000 documents)
router.get('/employees/:id', async (req, res) => {
  const t0 = performance.now();
  try {
    const db = getDB();
    const id = req.params.id.trim();

    // Look up by _id (e.g. EMP1000000) or numeric row_id
    let query = { _id: id };
    if (!isNaN(id) && !id.startsWith('EMP')) {
      query = { row_id: parseInt(id, 10) };
    }

    const employee = await db.collection('employees').findOne(query);
    const latencyMs = (performance.now() - t0).toFixed(2);

    if (!employee) {
      return res.status(404).json({
        error: `Employee with ID '${id}' not found`,
        latency_ms: parseFloat(latencyMs)
      });
    }

    res.json({
      ...employee,
      latency_ms: parseFloat(latencyMs)
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 6. Paginated employee search/filter
router.get('/employees', async (req, res) => {
  try {
    const db = getDB();
    const page = Math.max(1, parseInt(req.query.page || '1', 10));
    const limit = Math.min(100, Math.max(1, parseInt(req.query.limit || '20', 10)));
    const skip = (page - 1) * limit;

    const filter = {};
    if (req.query.department) {
      filter.department = req.query.department;
    }
    if (req.query.status) {
      filter.status = req.query.status;
    }
    if (req.query.work_mode) {
      filter.work_mode = req.query.work_mode;
    }

    const [items, total] = await Promise.all([
      db.collection('employees').find(filter).skip(skip).limit(limit).toArray(),
      db.collection('employees').countDocuments(filter)
    ]);

    res.json({
      page,
      limit,
      total,
      total_pages: Math.ceil(total / limit),
      items
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

export default router;
