select FRV.responsibility_name,FRV.Application_id,FAT.application_name 
from fnd_application_tl FAT,FND_RESPONSIBILITY_VL FRV
where FRV.Application_id=FAT.Application_id
and FRV.responsibility_name like '%GL%';
