import ftplib
import os
import re
import sys


class Ftp:
    def __init__(self, s_host, s_user, s_pass, i_timeout=5):

        self.s_host = s_host

        try:
            self.o_ftp = ftplib.FTP(host=s_host, user=s_user, passwd=s_pass, timeout=i_timeout)
            print 'FTP> %s connected...' % s_host
        except ftplib.all_errors:
            print 'ERROR: FTP server not found.'
            sys.exit()

    def __str__(self):
        s_output = '<Ftp: %s>' % self.o_ftp.host
        return s_output

    def cwd(self, s_dirname):
        # todo: add error handling code when s_dirname doesn't exist
        self.o_ftp.cwd(s_dirname)

    def pwd(self):
        """
        Method to get the current working directory of the ftp.

        :return: An string indicating the current directory. i.e. '/abc/foo/'
        """

        return self.o_ftp.pwd()

    def list_elements(self, s_root=''):
        """
        Method to return a list containing all the FileEntry objects corresponding to the elements in the CWD of the
        ftp.

        :return: A list of FileEntry objects.
        """

        s_current_dir = self.o_ftp.pwd()

        if s_root != '':
            self.cwd(s_root)

        lo_elements = []

        for s_line in self.o_ftp.nlst():

            o_file_entry = FileEntry(self, s_root, s_line, s_method='from_nlst_line')

            # Only actual files, 'f', and directories, 'd' are kept. Fake dirs like '..' are avoid.
            if o_file_entry.s_type in ('f', 'd'):
                lo_elements.append(o_file_entry)

        self.cwd(s_current_dir)

        return lo_elements

    def list_dirs(self, s_root):
        """
        Similar to list_elements method but only directory elements are returned.

        :return: A list of FileEntry objects.
        """

        lo_elements = self.list_elements(s_root)

        lo_dirs = []

        for o_element in lo_elements:
            if o_element.s_type == 'd':
                lo_dirs.append(o_element)

        return lo_dirs

    def list_files(self, s_root):
        """
        Similar to list_elements method but only file elements are returned.

        :return: A list of FileEntry objects.
        """

        lo_elements = self.list_elements(s_root)

        lo_files = []

        for o_element in lo_elements:
            if o_element.s_type == 'f':
                lo_files.append(o_element)

        return lo_files

    def download_file(self, o_file_entry):
        """
        Method to download a file from the ftp server. The file is downloaded without any kind of folder structure to
        the same place where the script is being executed from.

        :param o_file_entry: I must be a real file entry (self.s_type = 'f'). Otherwise an error is printed.

        :return: Nothing.
        """

        if o_file_entry.s_type == 'f':
            s_original_path = self.o_ftp.pwd()
            self.o_ftp.cwd(o_file_entry.s_root)

            s_command = 'RETR %s' % o_file_entry.s_full_name

            print 'ftp> %s' % s_command

            o_download_file = open(o_file_entry.s_full_name, 'wb')
            self.o_ftp.sendcmd('TYPE I')
            self.o_ftp.retrbinary(s_command, o_download_file.write)

            o_download_file.close()

            self.o_ftp.cwd(s_original_path)

        elif o_file_entry.s_type == 'd':
            print 'ERROR: You are trying to download a directory as a file'

        else:
            print 'ERROR: You are trying to download a non-existent file entry'

    def delete_file(self, o_file_entry):
        """
        Method to delete a file from the ftp server.

        :param o_file_entry: I must be a real file entry (self.s_type = 'f'). Otherwise an error is printed.

        :return: Nothing.
        """
        if o_file_entry.s_type == 'f':
            s_original_path = self.o_ftp.pwd()
            self.o_ftp.cwd(o_file_entry.s_root)

            s_command = 'DELE %s' % o_file_entry.s_full_name

            print 'ftp> %s' % s_command

            #self.o_ftp.sendcmd('TYPE I')
            self.o_ftp.delete(o_file_entry.s_full_name)

            self.o_ftp.cwd(s_original_path)

        elif o_file_entry.s_type == 'd':
            print 'ERROR: You are trying to delete a directory as a file'
        else:
            print 'ERROR: You are trying to delete a non-existent file entry'

    def delete_dir(self, o_file_entry):

        if o_file_entry.s_type == 'd':
            # BIG WARNING HERE: After deleting a directory you are returned to the parent folder of the deleted one!!!
            self.o_ftp.cwd(o_file_entry.s_root)

            print 'Trying to delete %s' % o_file_entry.s_full_name
            self.o_ftp.rmd(o_file_entry.s_full_name)

            self.o_ftp.dir()

        elif o_file_entry.s_type == 'f':
            print 'ERROR: You are trying to delete a file as a directory'
        else:
            print 'ERROR: You are trying to delete a non-existent file entry as a directory'

    def sendcmd(self, s_cmd):
        self.o_ftp.sendcmd(s_cmd)

    def retrbinary(self, s_cmd, s_callback, i_blocksize=8192, i_rest=None):
        self.o_ftp.retrbinary(cmd=s_cmd, callback=s_callback, blocksize=i_blocksize, rest=i_rest)


class FileEntry:

    def __init__(self, o_ftp, s_root, s_input, s_method='from_nlst_line'):

        # Variable definitions
        self.o_ftp = None                   # Every file entry points to an ftp object.

        self.i_size = 0                     # File size (in bytes?)
        self.s_date = ''                    # File date (not used by now)
        self.s_full_name = ''               # Full file name i.e. 'picture.jpg'
        self.s_name = ''                    # Short file name i.e. 'picture'
        self.s_ext = ''                     # File extension i.e. 'jpg'
        self.s_type = 'u'                   # '-' for file, 'd' for directory, 'u' for non-existent or unknown element
        self.s_permission = ''              # File permission string i.e. 'rwxrwxrwx'
        self.s_unknown = ''                 # Unknown parameter appearing before 'group user' in ftp listing (1 typical)
        self.s_group = ''                   # File owner group
        self.s_user = ''                    # File owner user

        self.s_root = ''                    # Full root path of the FileEntry
        self.s_full_path = ''               # Full path of the FileEntry

        # Variable population (1/2) - Basic population
        if isinstance(o_ftp, Ftp):
            self.o_ftp = o_ftp
        else:
            print 'ERROR: The o_ftp parameter is not a Ftp object.'
            sys.exit()

        # Variable population (1/2) - Basic population
        # s_root, s_input sanitization
        s_root = s_root.rstrip('/')
        s_input = s_input.rstrip('/')

        if s_method == 'from_nlst_line':
            self._from_nlst_line(s_root, s_input)

        elif s_method == 'from_path':
            s_path = '/'.join([s_root, s_input])
            s_path = s_path.rstrip('/')

            self._from_path(s_path)

    def _from_nlst_line(self, s_root, s_line):
        if s_line != '..':
            s_size_month_day_year_name = s_line.rpartition('    ')[2]
            s_permission_unknown_group_user = s_line.rpartition('    ')[0]

            self.i_size = int(s_size_month_day_year_name.split(' ')[0])
            self.s_date = ''  # TODO: Read date values and build a proper date object
            self.s_full_name = s_size_month_day_year_name.split(' ', 5)[4]

            if self.s_full_name.find('.') != -1:
                self.s_name = self.s_full_name.rpartition('.')[0]
                self.s_ext = self.s_full_name.rpartition('.')[2]
            else:
                self.s_name = self.s_full_name
                self.s_ext = ''

            s_sanitized_permission_unknown_group_user = re.sub(' +', ' ', s_permission_unknown_group_user)
            self.s_permission = s_sanitized_permission_unknown_group_user.split(' ')[0][1:]

            # Instead of the standard '-' for files, I prefer to use 'f'
            self.s_type = s_sanitized_permission_unknown_group_user.split(' ')[0][0]
            if self.s_type == '-':
                self.s_type = 'f'

            self.s_unknown = s_sanitized_permission_unknown_group_user.split(' ')[1]
            self.s_group = s_sanitized_permission_unknown_group_user.split(' ')[2]
            self.s_user = s_sanitized_permission_unknown_group_user.split(' ')[3]

            self.s_root = s_root
            self.s_full_path = '%s/%s' % (self.s_root, self.s_full_name)

    def _from_path(self, s_path):
        """
        Method to build the object using a path as the input.

        :param s_path: Path of the element. i.e. 'Home/abc/picture.jpg'

        :return: Nothing
        """

        s_root = s_path.rpartition('/')[0]
        s_full_name = s_path.rpartition('/')[2]

        lo_all_elements = self.o_ftp.list_elements(s_root)
        o_matched_element = None

        for o_element in lo_all_elements:
            if o_element.s_full_name == s_full_name:
                o_matched_element = o_element
                break

        if o_matched_element is not None:
            self.copy_from(o_matched_element)

    def __str__(self):
        s_output = ''
        s_output += '        FTP: %s\n' % self.o_ftp.s_host
        s_output += '  Full Path: %s\n' % self.s_full_path
        s_output += '       Root: %s\n' % self.s_root
        s_output += '       Type: %s\n' % self.s_type
        s_output += '  Full Name: %s\n' % self.s_full_name
        s_output += '       Size: %i\n' % self.i_size
        s_output += 'Permissions: %s\n' % self.s_permission
        s_output += '      Group: %s\n' % self.s_group
        s_output += '       User: %s\n' % self.s_user

        return s_output

    def copy_from(self, o_source):

        # TODO: Add code to detect in o_source object is actually a FileEntry object.
        if o_source is not None:
            self.o_ftp = o_source.o_ftp
            self.i_size = o_source.i_size
            self.s_date = o_source.s_date
            self.s_full_name = o_source.s_full_name
            self.s_name = o_source.s_name
            self.s_ext = o_source.s_ext
            self.s_type = o_source.s_type
            self.s_permission = o_source.s_permission
            self.s_unknown = o_source.s_unknown
            self.s_group = o_source.s_group
            self.s_user = o_source.s_user
            self.s_root = o_source.s_root
            self.s_full_path = o_source.s_full_path

    def download(self, s_mode='flat', s_dest=''):
        """
        Method to download a file from the FTP and save it in the local drive.

        :param s_mode: 'flat', the file is downloaded in the same folder, without any kind of structure. 'tree', the
                        file is downloaded replicating the FTP structure in the destination folder.

        :param s_dest: Local root folder where the file/directory is going to be downloaded. i.e. '/user/john/desktop'

        :return: Nothing.
        """

        if self.s_type == 'f':
            s_original_path = self.o_ftp.pwd()

            self.o_ftp.cwd(self.s_root)

            s_ftp_command = 'RETR %s' % self.s_full_name

            s_dest_file = os.path.join(s_dest, self.s_full_name)
            o_dest_file = open(s_dest_file, 'wb')

            self.o_ftp.sendcmd('TYPE I')
            self.o_ftp.retrbinary(s_ftp_command, o_dest_file.write)

            o_dest_file.close()

            print 'Downloaded: %s %s' % (s_dest_file, human_size(os.path.getsize(s_dest_file)))

            self.o_ftp.cwd(s_original_path)


def human_size(i_value):

    s_output = ''

    for s_unit in ('bytes', 'KB', 'MB', 'GB'):

        if -1024.0 < i_value < 1024.0:
            if s_unit != 'bytes':
                s_output = '%3.1f %s' % (i_value, s_unit)
            else:
                s_output = '%3.0f %s' % (i_value, s_unit)

            break

        i_value /= 1024.0

    if s_output == '':
        s_output = '%3.1f %s' % (i_value, 'TB')

    return s_output



