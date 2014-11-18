#
# Provides completion suggestions for C/C++ languages
# based on clang output
#

import sublime, sublime_plugin, os, ntpath, subprocess, codecs, re

class ClangAutoComplete(sublime_plugin.EventListener):

	def __init__(self):
		self.load_settings()
		self.compl_regex = re.compile("COMPLETION: ([\s\S]+) : ([\s\S]+)")
		self.file_ext = re.compile("[\s\S]+\.(\w+)")

	def load_settings(self):
		# Variable $project_base_path in settings will be replaced by sublime's project path
		settings = sublime.load_settings("ClangAutoComplete.sublime-settings")
		
		project_path=""
		if sublime.active_window().project_data() is not None:
			project_path = (sublime.active_window().project_data().get("folders")[0].get("path"))

		self.tmp_file_path    = settings.get("tmp_file_path")
		self.default_encoding = settings.get("default_encoding")
		self.selectors        = settings.get("selectors")
		self.include_dirs     = settings.get("include_dirs")
		for i in range(0, len(self.include_dirs)):
			self.include_dirs[i] = re.sub("(\$project_base_path)", project_path, self.include_dirs[i])

	def on_query_completions(self, view, prefix, locations):
		
		# Find exact Line:Column position of cursor for clang
		pos = view.sel()[0].begin()
		body = view.substr(sublime.Region(0, view.size()))

		# Verify that character under the cursor is one allowed selector
		if any(e in body[pos-1:pos] for e in self.selectors) == False:
			return []
		line_pos = body[:pos].count('\n')+1
		char_pos = pos-body.rfind("\n", 0, len(body[:pos]))


		# Create temporary file name that reflects what user is currently typing
		enc = view.encoding()
		if  enc == "Undefined":
			enc = self.default_encoding
		with open(self.tmp_file_path, "w", encoding=enc) as tmp_file:
			tmp_file.write(body)

		# Find file type (.c/.cpp) to set relevant clang flags 
		file_ext = re.findall(self.file_ext, view.file_name())
		cpp_flags = ""
		if len(file_ext) > 0 and file_ext[0] == "cpp":
			cpp_flags = "-x c++"

		# Build clang command
		clang_bin = "clang++"
		clang_flags = "-cc1 " + cpp_flags + " -fsyntax-only"
		clang_target = "-code-completion-at " + self.tmp_file_path+":"+str(line_pos)+":"+str(char_pos ) +" "+self.tmp_file_path
		clang_includes=" -I ."
		for dir in self.include_dirs:
			clang_includes += " -I " + dir

		# Execute clang command, exit 0 to suppress error from check_output()
		clang_cmd = clang_bin + " " + clang_flags + " " + clang_target + clang_includes
		output = subprocess.check_output(clang_cmd+";exit 0", shell=True)

		# Process clang output, find COMPLETION lines and return them with a little formating
		output_text = ''.join(map(chr,output))
		output_lines = output_text.split('\n')
		result = []
		longest_len = 0
		for line in output_lines:
			tmp_res=re.findall(self.compl_regex, line)
			if len(tmp_res) <= 0:
				continue
			if len(tmp_res[0][0]) > longest_len:
				longest_len = len(tmp_res[0][0])
			result.append([tmp_res[0][1], tmp_res[0][0]])

		for tuple in result:
			tuple[0] = tuple[1].ljust(longest_len) + " - " + tuple[0]
		return (result, sublime.INHIBIT_WORD_COMPLETIONS)



