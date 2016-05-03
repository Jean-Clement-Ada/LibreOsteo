import logging
import csv
from django.utils.translation import ugettext_lazy as _
import random
from libreosteoweb.models import Patient, Examination, ExaminationType, ExaminationStatus
from datetime import date, datetime
from .utils import enum, Singleton

logger = logging.getLogger(__name__)

class Extractor(object):

    def extract(self, instance):
        """
        return a dict with key patient and examination which gives some extract of the content,
        with list of dict which contains line number and the content.
        """
        result = {}

        extract_patient = self.extract_file(instance.file_patient)
        extract_examination = self.extract_file(instance.file_examination)

        result['patient'] = extract_patient
        result['examination'] = extract_examination

        return result

    def analyze(self, instance):
        """
        return a dict with key patient, and examination, which indicates if :
         - the expected file has the correct type.
         - the file is is_valid
         - the file is not is_empty
         - list of errors if found.
        """
        logger.info("* Analyze the instance")
        result = {}

        (type_file, is_valid, is_empty, errors) = self.analyze_file(instance.file_patient)
        result['patient'] = (type_file, is_valid, is_empty, errors)
        
        (type_file, is_valid, is_empty, errors) = self.analyze_file(instance.file_examination)
        result['examination'] = (type_file, is_valid, is_empty, errors)
        return result

    def analyze_file(self, file):
        if not bool(file) :
            return ('', False, True, [])

        try:
            handler = AnalyzerHandler()
            report = handler.analyze(file)
        except:
            logger.exception('Analyze failed.')
            return ('', False, True, [_('Analyze failed on this file')])

        if report.type == FileCsvType.PATIENT:
            return ('patient', report.is_valid, report.is_empty, [])
        if report.type == FileCsvType.EXAMINATION :
            return ('examination', report.is_valid, report.is_empty, [])
        else :
            return ('patient', False, True, [_('Cannot recognize the patient file')])

    def extract_file(self, file):
        if not bool(file) :
            return {}
        result = {}
        try :
            content = FileContentProxy().get_content(file, line_filter=filter)
            nb_row = content['nb_row'] - 1
            if nb_row > 0:
                idx = sorted(random.sample(range(1, nb_row+1), min(5, nb_row)))
                logger.info("indexes = %s "% idx)
                for i in idx:
                    result['%s' % (i+1)] = content['content'][i-1]
        except:
            logger.exception('Extractor failed.')
        logger.info("result is %s" % result)
        return result

    def get_content(self, file):
        return FileContentProxy().get_content(file, line_filter=filter)

    def unproxy(self,file):
        FileContentProxy().unproxy(file, line_filter=filter)



def filter( line):
    result_line = None
    try:
        result_line = line.decode('utf-8')
    except:
        pass
    if result_line is None :
        try:
            result_line = line.decode('iso-8859-1')
        except:
            result_line = _('Cannot read the content file. Check the encoding.')
    return result_line





FileCsvType = enum(
    'FileCsvType',
    'PATIENT',
    'EXAMINATION'
)


class AnalyzeReport(object):
    def __init__(self, is_empty, is_valid, type):
        self.is_empty = is_empty
        self.is_valid = is_valid
        self.type = type

    def is_empty(self):
        return self.is_empty
    def is_valid(self):
        return self.is_valid
    def type(self):
        return self.type

class Analyzer(object):
    """
        Performs the analyze on the content.
        It should be inherited.
    """
    identifier = None
    type = None

    def __init__(self, content=None):
        self.content = content

    def is_instance(self):
        if self.content is not None :
            try :
                self._parse_header(self.content['header'])
                return True
            except ValueError:
                return False
        return False
    def _parse_header(self, header):
        unicode(header[:]).lower().index(self.__class__.identifier)

    def get_report(self):
        is_empty = self.content.nb_row <= 1
        #is_valid should check the number of columns
        is_valid = len(self.content.header) ==  self.__class__.field_number

        return AnalyzeReport(is_empty, is_valid, self.__class__.type)

class AnalyzerPatientFile(Analyzer):
    identifier = 'nom de famille'
    type = FileCsvType.PATIENT
    field_number = 23
    def __init__(self, content=None):
        super(self.__class__, self).__init__(content=content)

class AnalyzerExaminationFile(Analyzer):
    identifier = 'conclusion'
    type = FileCsvType.EXAMINATION
    field_number = 14
    def __init__(self, content=None):
        super(self.__class__, self).__init__(content=content)


class FileContentAdapter(dict):
    def __init__(self, ourfile, line_filter=None):
        self.file = ourfile
        self['content'] = None
        self.filter = line_filter
        if self.filter is None :
            self.filter = self.passthrough
    def __getattr__(self, attr):
        return self[attr]
    def get_content(self):
        if self['content'] is None:
            reader = self._get_reader()
            rownum = 0
            header = None
            content = []
            for row in reader:
                print row
                # Save header row.
                if rownum == 0:
                    header = [self.filter(c) for c in row]
                else :
                    content.append([self.filter(c) for c in row])
                rownum += 1
            self.file.close()
            self['content'] = content
            self['nb_row'] = rownum
            self['header'] = header
        return self

    def _get_reader(self):
        if not bool(self.file):
            return None
        self.file.open(mode='rb')
        logger.info("* Try to guess the dialect on csv")
        dialect = csv.Sniffer().sniff(self.file.read(1024))
        self.file.seek(0)
        reader = csv.reader(self.file, dialect)
        return reader
    def passthrough(self,line):
        return line

class FileContentKey(object):
    def __init__(self, ourfile, line_filter):
        self.file = ourfile
        self.line_filter = line_filter
    def __hash__(self):
        return hash((self.file, self.line_filter))

    def __eq__(self, other):
        return (self.file, self.line_filter) == (other.file, other.line_filter)

    def __ne__(self, other):
        # Not strictly necessary, but to avoid having both x==y and x!=y
        # True at the same time
        return not(self == other)

class FileContentProxy(object):
    __metaclass__ = Singleton
    file_content = {}
    def get_content(self, ourfile, line_filter=None):
        key = FileContentKey(ourfile, line_filter)
        try:
            return self.file_content[key]
        except KeyError:
            self.file_content[key] = FileContentAdapter(ourfile, line_filter).get_content()
            return self.file_content[key]

    def unproxy(self, ourfile,line_filter=None):
        key = FileContentKey(ourfile, line_filter)
        try :
            self.file_content[key] = None
        except :
            pass




class AnalyzerHandler(object):
    analyzers = [AnalyzerPatientFile, AnalyzerExaminationFile]
    def analyze(self, ourfile):
        if not bool(ourfile) :
            return AnalyzeReport(False, False, None)
        content = self.get_content(ourfile)
        for analyzer in self.analyzers:
            instance = analyzer(content)
            if instance.is_instance() :
                return instance.get_report()
        return AnalyzeReport(False,False, None)
    def get_content(self, ourfile):
        return FileContentProxy().get_content(ourfile, line_filter=filter)





    def filter(self, line):
        result_line = None
        try:
            result_line = line.decode('utf-8')
        except:
            pass
        if result_line is None :
            try:
                result_line = line.decode('iso-8859-1')
            except:
                result_line = _('Cannot read the content file. Check the encoding.')
        return result_line


class InvalidIntegrationFile(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class IntegratorHandler(object):
    def integrate(self, file, file_additional=None, user=None):
        integrator = IntegratorFactory().get_instance(file)
        if integrator is None:
            raise InvalidIntegrationFile("This file %s is not valid to be integrated." % (file))

        result = integrator.integrate(file, file_additional=file_additional, user=user)
        return result

    def post_processing(self, files):
        extractor = Extractor()
        for f in files :
            extractor.unproxy(f)
        



class IntegratorFactory(object):
    def __init__(self, serializer_class=None):
        self.extractor = Extractor()
        self.serializer_class = serializer_class
    def get_instance(self, file):
        result = self.extractor.analyze_file(file)
        if not result[1]:
            return None
        if result[0] == 'patient':
            from .serializers import PatientSerializer
            return IntegratorPatient(serializer_class=PatientSerializer)
        elif result[0] == 'examination':
            from .serializers import ExaminationSerializer
            return IntegratorExamination(serializer_class=ExaminationSerializer)

class FilePatientFactory(object):
    def __init__(self):
        from .serializers import PatientSerializer
        self.serializer_class = PatientSerializer

    def get_serializer(self, row):
        data = {
                'family_name' : row[1],
                'original_name' : row[2],
                'first_name' : row[3],
                'birth_date' : self.get_date(row[4]),
                'sex' : self.get_sex_value(row[5]),
                'address_street' : row[6],
                'address_complement' : row[7],
                'address_zipcode' : row[8],
                'address_city' : row[9],
                'phone' : row[10],
                'mobile_phone' : row[11],
                'job' : row[12],
                'hobbies' : row[13],
                'smoker'  : self.get_boolean_value(row[14]),
                'laterality'  : self.get_laterality_value(row[15]),
                'important_info' : row[16],
                'current_treatment' : row[17],
                'surgical_history' : row[18],
                'medical_history' : row[19],
                'family_history' : row[20],
                'trauma_history' : row[21],
                'medical_report' : row[22],
                'creation_date' : self.get_default_date(),
            }
        serializer = self.serializer_class(data=data)
        return serializer
    def get_sex_value(self, value):
        if value.upper() == 'F':
            return 'F'
        else :
            return 'M'
    def get_laterality_value(self, value):
        if value.upper() == 'G' or value.upper() == 'L':
            return 'L'
        else :
            return 'R'
    def get_boolean_value(self, value):
        if value.lower() == 'o' or value.lower() == 'oui' or value.lower() == 'true' or value.lower() == 't':
            return True
        else :
            return False
    def get_default_date(self):
        return date(2011, 01, 01)
    def get_date(self, value):
        f = "%d/%m/%Y"
        return datetime.strptime(value, f).date()


class AbstractIntegrator(object):
    def integrate(self, file, file_additional=None,user=None):
        pass

class IntegratorPatient(AbstractIntegrator):
    def __init__(self, serializer_class=None):
        self.extractor = Extractor()
        self.serializer_class=serializer_class
    def integrate(self, file, file_additional=None, user=None):
        content = self.extractor.get_content(file)
        nb_line = 0
        errors = []
        factory = FilePatientFactory()

        for idx, r in enumerate(content['content']):
            logger.info("* Load line from content")
            serializer = factory.get_serializer(r)
            if serializer.is_valid():
                serializer.save()
                nb_line += 1
            else :
                # idx + 2 because : we have header and the index start from 0
                # To have the line number we have to add 2 to the index....
                errors.append((idx+2, serializer.errors))
                logger.info("errors detected, data is = %s "% serializer.initial_data)
        return ( nb_line, errors)


class IntegratorExamination(AbstractIntegrator):
    def __init__(self, serializer_class=None):
        self.extractor = Extractor()
        self.serializer_class=serializer_class
        self.patient_table = None
    def integrate(self, file, file_additional=None, user=None):
        if file_additional is None:
            return (0, [_('Missing patient file to integrate it.')])
        content = self.extractor.get_content(file)
        nb_line = 0
        errors = []
        for idx, r in enumerate(content['content']):
            logger.info("* Load line from content")
            try:
                patient = self.get_patient(int(r[0]), file_additional)
                data = {
                    'date': self.get_date(r[1], with_time=True),
                    'reason': r[2],
                    'reason_description': r[3],
                    'orl' : r[4],
                    'visceral': r[5],
                    'pulmo' : r[6],
                    'uro_gyneco' : r[7],
                    'periphery' : r[8],
                    'general_state' : r[9],
                    'medical_examination' : r[10],
                    'diagnosis' : r[11],
                    'treatments' : r[12],
                    'conclusion' : r[13],
                    'patient' : patient,
                    'therapeut': user.id,
                    'type' : ExaminationType.NORMAL,
                    'status' : ExaminationStatus.NOT_INVOICED,
                    'status_reason': _('Imported examination'),
                }
                serializer = self.serializer_class(data=data)
                if serializer.is_valid():
                    serializer.save()
                    nb_line += 1
                else :
                    # idx + 2 because : we have header and the index start from 0
                    # To have the line number we have to add 2 to the index....
                    errors.append((idx+2, serializer.errors))
                    logger.info("errors detected, data is = %s "% data)
            except ValueError as e:
                logger.exception("Exception when creating examination.")
                errors.append((idx+2, { 'general_problem' : _('There is a problem when reading this line :') + unicode(e) } ))
            except :
                logger.exception("Exception when creating examination.")
                errors.append((idx+2, { 'general_problem' : _('There is a problem when reading this line.') } ) )
        return ( nb_line, errors)
    
    def get_date(self, value, with_time=False):
        f = "%d/%m/%Y"
        if with_time :
            return datetime.strptime(value, f)
        return datetime.strptime(value, f).date()

    def get_patient(self, numero, file_patient):
        if not bool(file_patient):
            return None
        if self.patient_table is None:
            self._build_patient_table(file_patient)
        return self.patient_table[numero]

    def _build_patient_table(self, file_patient):
        content = self.extractor.get_content(file_patient)
        self.patient_table = {}
        factory = FilePatientFactory()
        for c in content['content']:
            serializer = factory.get_serializer(c)
            # remove validators to get a validated data through filters
            serializer.validators = []
            serializer.is_valid()
            self.patient_table[int(c[0])] = Patient.objects.filter(family_name=serializer.validated_data['family_name'],
                first_name=serializer.validated_data['first_name'],
                birth_date=serializer.validated_data['birth_date']
                )

            logger.info("found patient %s " % self.patient_table[int(c[0])])


