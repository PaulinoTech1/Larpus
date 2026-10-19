import unittest
from unittest.mock import patch
from tests import test_knowledge as fixtures
from runtime import knowledge

class ConnectionReuseTests(unittest.TestCase):
 setUp=fixtures.KnowledgeTests.setUp
 pin=fixtures.KnowledgeTests.pin
 def test_hybrid_and_continuation_share_verified_connection(self):
  class Engine:
   bm25=10;semantic=6;deadline=1;minimum=0
   def neighbors(self,q,limit):return [2]
   def rerank(self,q,passages,deadline):return [1.]*len(passages)
  original=knowledge.database
  with patch.object(knowledge,'_engine',return_value=Engine()),patch.object(knowledge,'database',wraps=original) as opened:
   found=knowledge.retrieve('home-assistant','side channel attacks')
  self.assertTrue(found)
  self.assertEqual(opened.call_count,1,'Retrieval must reuse one freshly verified read-only connection')
 def test_each_new_request_revalidates_and_rejects_changed_database(self):
  with patch.object(knowledge,'_engine',return_value=None):
   self.assertTrue(knowledge.retrieve('home-assistant','side channel attacks'))
   with self.database.open('ab') as stream:stream.write(b'changed')
   with self.assertRaises(ValueError):knowledge.retrieve('home-assistant','side channel attacks')

 def test_connection_closes_when_passage_screening_fails(self):
  import sqlite3
  captured=[];original=knowledge.database
  def opened():
   connection=original();captured.append(connection);return connection
  with patch.object(knowledge,'_engine',return_value=None),patch.object(knowledge,'database',side_effect=opened),patch.object(knowledge,'inspect_reference',side_effect=ValueError('rejected')):
   with self.assertRaises(ValueError):knowledge.retrieve('home-assistant','side channel attacks')
  self.assertEqual(len(captured),1)
  with self.assertRaises(sqlite3.ProgrammingError):captured[0].execute('SELECT 1')

 def test_verified_connection_enables_bounded_read_only_mapping(self):
  import sqlite3
  from contextlib import closing
  with closing(knowledge.database()) as connection:
   self.assertEqual(connection.execute('PRAGMA mmap_size').fetchone()[0],256*1024*1024)
   self.assertEqual(connection.execute('PRAGMA query_only').fetchone()[0],1)
   with self.assertRaises(sqlite3.OperationalError):connection.execute('DELETE FROM chunks')

 def test_continuations_that_cannot_fit_do_not_rehash_database(self):
  import sqlite3
  text='side channel attacks and error handling. '*30
  with sqlite3.connect(self.database) as connection:
   for i in range(6):connection.execute('INSERT INTO chunks VALUES (?,?,?,?,?,?,?)',('long-'+str(i),'Long reference','https://example.com','2026','page 1 offset 0',text,'home-assistant'))
  connection.close();self.pin();original=knowledge.database
  with patch.object(knowledge,'_engine',return_value=None),patch.object(knowledge,'database',wraps=original) as opened:
   found=knowledge._retrieve('home-assistant','side channel attacks',budget=100)
  self.assertEqual(found,[])
  self.assertEqual(opened.call_count,1,'Rejected continuation candidates must not reopen and rehash the corpus')
