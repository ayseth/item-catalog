import sys

from sqlalchemy import Column, ForeignKey, Integer, String

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()

class catalog(Base):
	__tablename__='catalog'

	id=Column(Integer, primary_key=True)
	title = (Column(String(250), nullable=False))
	description = Column(String(250))
	category = Column(String(250))
	picture = Column(String(250))
	link = Column(String(250))
	cover_pic = Column(String(250))

	@property
	def serialize(self):
		return {
		'id' : self.id,
		'title' : self.title,
		'description' : self.description,
		'category' : self.category,
		'picture' : self.picture,
		
		}
	



engine = create_engine('sqlite:///catalog.db')
Base.metadata.create_all(engine)