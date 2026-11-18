from . import mock, meshy, triposr, hunyuan

def generate(job, job_dir, destination, *, approve_paid=False, approve_upload=False):
    provider=job.get('provider','mock')
    if provider=='mock': return mock.generate(destination)
    if provider=='meshy': return meshy.generate(job,job_dir,destination,approve_paid=approve_paid,approve_upload=approve_upload)
    if provider == "triposr":
        return triposr.generate(job, job_dir, destination)
    if provider == "hunyuan":
        return hunyuan.generate(job, job_dir, destination)
    raise ValueError('Unknown provider')
